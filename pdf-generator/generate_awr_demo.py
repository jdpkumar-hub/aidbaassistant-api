#!/usr/bin/env python3
"""CLI: generate sample enterprise Oracle AWR PDF report."""

import argparse
from pathlib import Path

from awr_pdf import demo_awr_report_data, generate_awr_pdf


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate AI DBA Assistant AWR performance PDF report"
    )
    parser.add_argument(
        "-o",
        "--output",
        default="output/awr_performance_report.pdf",
        help="Output PDF path",
    )
    args = parser.parse_args()

    data = demo_awr_report_data()
    path = generate_awr_pdf(data, args.output)
    print(f"Generated: {Path(path).resolve()}")


if __name__ == "__main__":
    main()
