#!/usr/bin/env python3
"""Wrapper for candidate-vs-adjudicated survey rubric evolution runs."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-file", type=Path, required=True)
    parser.add_argument("--adjudicated-file", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--sheet", default="A1")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    script = Path(__file__).resolve().parents[2] / "cleaning-survey-quality" / "scripts" / "run_quality_loop.py"
    cmd = [
        sys.executable,
        str(script),
        "--candidate-file",
        str(args.candidate_file.expanduser().resolve()),
        "--adjudicated-file",
        str(args.adjudicated_file.expanduser().resolve()),
        "--output-dir",
        str(args.output_dir.expanduser().resolve()),
        "--sheet",
        args.sheet,
    ]
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
