from __future__ import annotations

from pathlib import Path

import click
import pandas as pd

from .coverage import coverage_report
from .dedupe import dedupe_against
from .fingerprint import compute_fingerprint
from .normalize import normalize_text
from .validate import validate_frame


@click.group()
def cli() -> None:
    """mock-content CLI."""


@cli.command("validate")
@click.argument("file", type=click.Path(exists=True, path_type=Path))
def validate_cmd(file: Path) -> None:
    df = pd.read_csv(file, dtype=str).fillna("")
    errors = validate_frame(df)
    if errors:
        for e in errors:
            click.echo(e)
        raise SystemExit(1)
    click.echo("OK")


@cli.command("fingerprint")
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option("--out", type=click.Path(path_type=Path))
def fingerprint_cmd(file: Path, out: Path | None) -> None:
    df = pd.read_csv(file, dtype=str).fillna("")
    df["question_fingerprint"] = [compute_fingerprint(r.to_dict()) for _, r in df.iterrows()]
    dupes = df[df["question_fingerprint"].duplicated(keep=False)]
    if not dupes.empty:
        click.echo(f"warning: {len(dupes)} rows in fingerprint collisions", err=True)
    target = out or file.with_name(file.stem + "_with_fp.csv")
    df.to_csv(target, index=False)
    click.echo(str(target))


@cli.command("dedupe")
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option("--against", required=True, type=click.Path(exists=True, path_type=Path))
@click.option("--out", type=click.Path(path_type=Path))
def dedupe_cmd(file: Path, against: Path, out: Path | None) -> None:
    df = pd.read_csv(file, dtype=str).fillna("")
    snap = pd.read_csv(against, dtype=str).fillna("")
    report = dedupe_against(df, snap)
    target = out or file.with_name(file.stem + "_dedupe_report.csv")
    report.to_csv(target, index=False)
    click.echo(str(target))


@cli.command("normalize")
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option("--out", type=click.Path(path_type=Path))
def normalize_cmd(file: Path, out: Path | None) -> None:
    df = pd.read_csv(file, dtype=str, encoding="utf-8-sig").fillna("")
    for col in df.columns:
        df[col] = df[col].map(lambda x: normalize_text(x, collapse_whitespace=True))
    target = out or file.with_name(file.stem + "_clean.csv")
    df.to_csv(target, index=False)
    click.echo(str(target))


@cli.command("tag-coverage")
@click.argument("file", type=click.Path(exists=True, path_type=Path))
def tag_coverage_cmd(file: Path) -> None:
    df = pd.read_csv(file, dtype=str).fillna("")
    report = coverage_report(df)
    click.echo(report.to_csv(index=False))


@cli.command("sample-template")
@click.option("--out-dir", type=click.Path(path_type=Path), default=Path.cwd())
def sample_template_cmd(out_dir: Path) -> None:
    src = Path(__file__).resolve().parent.parent / "samples" / "starter.csv"
    dst = out_dir / "starter.csv"
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    click.echo(str(dst))
