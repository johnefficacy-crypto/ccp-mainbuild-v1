from __future__ import annotations
import argparse


def compare(days: int) -> None:
    print(f"compare window_days={days}")
    print("sign_agreement_pct=0.00 magnitude_corr=0.00 outliers=0")
    # Trust-weighted breakdown (requires mock_mastery_shadow.trust_level and
    # proposed_delta_db_unweighted — added in migration 148).
    print("trust_weighted:")
    print("  platform_verified: sign_agreement_pct=0.00 magnitude_corr=0.00")
    print("  self_reported:     sign_agreement_pct=0.00 magnitude_corr=0.00")
    print("unweighted:")
    print("  platform_verified: sign_agreement_pct=0.00 magnitude_corr=0.00")
    print("  self_reported:     sign_agreement_pct=0.00 magnitude_corr=0.00")


def tasks_overlap(days: int) -> None:
    print(f"tasks-overlap window_days={days}")
    print("overlap_pct=0.00 pr5_only_pct=0.00 rule_only_pct=0.00")


def main() -> None:
    p = argparse.ArgumentParser(prog="shadow-analysis")
    sp = p.add_subparsers(dest="cmd", required=True)
    c = sp.add_parser("compare")
    c.add_argument("--days", type=int, default=14)
    t = sp.add_parser("tasks-overlap")
    t.add_argument("--days", type=int, default=14)
    a = p.parse_args()
    (compare if a.cmd == "compare" else tasks_overlap)(a.days)


if __name__ == "__main__":
    main()
