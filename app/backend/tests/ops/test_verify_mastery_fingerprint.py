from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[4]
VERIFIER = REPO_ROOT / "scripts" / "verify_mastery_fingerprint.sh"


def run(
    args: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)

    return subprocess.run(
        args,
        cwd=cwd,
        env=merged_env,
        text=True,
        capture_output=True,
        check=check,
    )


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run(["git", *args], cwd=repo, check=check)


def run_verifier(
    repo: Path,
    *,
    expected_sha: str | None = None,
    skip_sha: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Invoke Bash with validated literal controls for Windows/MSYS compatibility."""
    commands = ["unset EXPECTED_SHA SKIP_SHA"]

    if expected_sha is not None:
        if (
            len(expected_sha) != 40
            or any(char not in "0123456789abcdefABCDEF" for char in expected_sha)
        ):
            raise ValueError("expected_sha must be exactly 40 hexadecimal characters")
        commands.append(f"export EXPECTED_SHA={expected_sha}")

    if skip_sha:
        commands.append("export SKIP_SHA=1")

    commands.append("exec bash scripts/verify_mastery_fingerprint.sh")

    return run(
        ["bash", "-c", "; ".join(commands)],
        cwd=repo,
        check=False,
    )


def build_fixture(tmp_path: Path, *, crlf_checkout: bool = False) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()

    git(repo, "init")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Verifier Test")

    write(repo / "src/a.txt", "alpha\n")
    write(repo / "src/b.txt", "beta\n")

    paths = ["src/a.txt", "src/b.txt"]
    records = "".join(
        f"{hashlib.sha256((repo / path).read_bytes()).hexdigest()}  {path}\n"
        for path in paths
    )
    combined = hashlib.sha256(records.encode("utf-8")).hexdigest()

    write(
        repo / "docs/ops/mastery_validation_fingerprint_manifest_v2.txt",
        f"# Combined digest: {combined}\n" + "\n".join(paths) + "\n",
    )
    write(
        repo / "docs/ops/mastery_validation_fingerprint_manifest_v2.attestation.txt",
        (
            "# File count      : 2\n"
            f"# Combined digest : {combined}\n"
            + records
        ),
    )
    write(
        repo / "docs/ops/pr7_shadow_gate_results.md",
        f"Fingerprint: {combined}\n",
    )
    write(
        repo / "docs/status/career-copilot-checklist.md",
        f"Fingerprint: {combined}\n",
    )

    target_script = repo / "scripts/verify_mastery_fingerprint.sh"
    target_script.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(VERIFIER, target_script)

    git(repo, "add", ".")
    git(repo, "commit", "-m", "fixture")
    head = git(repo, "rev-parse", "HEAD").stdout.strip()

    if crlf_checkout:
        git(repo, "config", "core.autocrlf", "true")

        for relative in [
            "src/a.txt",
            "src/b.txt",
            "docs/ops/mastery_validation_fingerprint_manifest_v2.txt",
            "docs/ops/mastery_validation_fingerprint_manifest_v2.attestation.txt",
            "docs/ops/pr7_shadow_gate_results.md",
            "docs/status/career-copilot-checklist.md",
        ]:
            path = repo / relative
            data = path.read_bytes().replace(b"\r\n", b"\n")
            path.write_bytes(data.replace(b"\n", b"\r\n"))

        # CRLF checkout normalization must not be treated as source drift.
        assert git(repo, "diff", "--quiet", check=False).returncode == 0

    return repo, head


@pytest.mark.parametrize("crlf_checkout", [False, True])
def test_verifier_passes_lf_and_crlf_checkouts(
    tmp_path: Path,
    crlf_checkout: bool,
) -> None:
    repo, head = build_fixture(tmp_path, crlf_checkout=crlf_checkout)

    result = run_verifier(repo, expected_sha=head)

    assert result.returncode == 0, result.stderr
    assert "OK: 2 files, combined freeze hash" in result.stdout
    assert f"@ {head}" in result.stdout


def test_verifier_rejects_wrong_expected_sha(tmp_path: Path) -> None:
    repo, _ = build_fixture(tmp_path)

    result = run_verifier(repo, expected_sha="0" * 40)

    assert result.returncode != 0
    assert "does not match EXPECTED_SHA" in result.stderr


def test_verifier_rejects_unstaged_fingerprinted_drift(tmp_path: Path) -> None:
    repo, _ = build_fixture(tmp_path)
    with (repo / "src/a.txt").open("a", encoding="utf-8") as handle:
        handle.write("unstaged drift\n")

    result = run_verifier(repo, skip_sha=True)

    assert result.returncode != 0
    assert "unstaged drift detected in fingerprinted file: src/a.txt" in result.stderr


def test_verifier_rejects_staged_fingerprinted_drift(tmp_path: Path) -> None:
    repo, _ = build_fixture(tmp_path)
    with (repo / "src/a.txt").open("a", encoding="utf-8") as handle:
        handle.write("staged drift\n")
    git(repo, "add", "src/a.txt")

    result = run_verifier(repo, skip_sha=True)

    assert result.returncode != 0
    assert "staged drift detected in fingerprinted file: src/a.txt" in result.stderr


def test_verifier_rejects_committed_stale_attestation(tmp_path: Path) -> None:
    repo, _ = build_fixture(tmp_path)
    attestation = (
        repo
        / "docs/ops/mastery_validation_fingerprint_manifest_v2.attestation.txt"
    )
    content = attestation.read_text(encoding="utf-8")
    attestation.write_text(
        content.replace(content.splitlines()[2].split()[0], "0" * 64, 1),
        encoding="utf-8",
        newline="\n",
    )
    git(repo, "add", str(attestation.relative_to(repo)))
    git(repo, "commit", "-m", "make attestation stale")

    result = run_verifier(repo, skip_sha=True)

    assert result.returncode != 0
    assert "per-file SHA-256 attestation mismatch" in result.stderr
