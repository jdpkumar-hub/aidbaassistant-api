#!/usr/bin/env python3
"""CLI: generate sample enterprise SQL DBA PDF report."""

import argparse
from pathlib import Path

from sql_dba_report import demo_report_data, generate_sql_dba_pdf


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate AI DBA Assistant SQL performance PDF report"
    )
    parser.add_argument(
        "-o",
        "--output",
        default="output/sql_performance_report.pdf",
        help="Output PDF path",
    )
    args = parser.parse_args()

    data = demo_report_data()
    path = generate_sql_dba_pdf(data, args.output)
    print(f"Generated: {path.resolve()}")


if __name__ == "__main__":
    main()
