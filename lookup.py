"""Command line helper to query the Flask API for player data."""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd
import requests

API_URL = "http://localhost:5000/api/players"
LOGGER = logging.getLogger(__name__)


def sanitise_filename(value: str) -> str:
    safe = "".join(ch for ch in value if ch.isalnum() or ch in ("-", "_"))
    return safe or "output"


def flatten_records(records: list[dict]) -> pd.DataFrame:
    flattened = []
    for record in records:
        data = dict(record)
        transfer = data.pop("Transfer", None)
        if isinstance(transfer, dict):
            for key, value in transfer.items():
                data[f"Transfer_{key}"] = value
        flattened.append(data)
    return pd.DataFrame(flattened)


def query_api(name: str | None = None, club: str | None = None) -> list[dict]:
    params = {}
    if name:
        params["name"] = name
    if club:
        params["club"] = club
    response = requests.get(API_URL, params=params, timeout=30)
    if response.status_code != 200:
        LOGGER.error("API request failed with status %s: %s", response.status_code, response.text)
        response.raise_for_status()
    return response.json()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", help="Player name to look up")
    parser.add_argument("--club", help="Club name to look up")
    parser.add_argument("--output-dir", default="artifacts", help="Directory for CSV output")
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))

    if not args.name and not args.club:
        LOGGER.error("Please provide either --name or --club")
        return 1

    records = query_api(name=args.name, club=args.club)
    if not records:
        print("No data found.")
        return 0

    df = flatten_records(records)
    if hasattr(df, "to_markdown"):
        print(df.to_markdown(index=False))
    else:
        print(df.to_string(index=False))

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.name:
        filename = sanitise_filename(args.name)
    else:
        filename = sanitise_filename(args.club)

    csv_path = output_dir / f"{filename}.csv"
    df.to_csv(csv_path, index=False)
    LOGGER.info("Saved results to %s", csv_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
