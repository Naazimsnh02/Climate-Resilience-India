"""Runs the full ingestion sequence once, in dependency order.
district_master must load before anything that joins against it.
"""
import subprocess
import sys
from pathlib import Path

STEPS = [
    "ingestion/load_district_master.py",
    "ingestion/gee_pull.py",
    "ingestion/mandi_prices.py",
    "ingestion/weather_current.py",
    "ingestion/rainfall_datagovin.py",
]


def main():
    root = Path(__file__).resolve().parent
    for step in STEPS:
        print(f"\n=== Running {step} ===")
        result = subprocess.run([sys.executable, str(root / step)], cwd=root)
        if result.returncode != 0:
            print(f"!!! {step} failed with exit code {result.returncode}, stopping.")
            sys.exit(result.returncode)


if __name__ == "__main__":
    main()
