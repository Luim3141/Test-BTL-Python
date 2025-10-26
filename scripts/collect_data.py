"""Collect Premier League player statistics and transfer values."""
from __future__ import annotations

import argparse
import logging


import pandas as pd

from btl.database import connect, create_table, upsert_rows
from btl.fbref import FbrefScraper
from btl.footballtransfers import FootballTransfersScraper
from btl.http import LOGGER as HTTP_LOGGER

LOGGER = logging.getLogger(__name__)


def build_players_table(connection, df: pd.DataFrame, table_name: str = "player_stats") -> None:
    schema: dict[str, str] = {}
    for column in df.columns:
        sample = df[column].dropna()
        if not sample.empty:
            if pd.api.types.is_numeric_dtype(sample):
                schema[column] = "REAL"
            else:
                schema[column] = "TEXT"
        else:
            schema[column] = "TEXT"
    if "Player" not in schema:
        schema["Player"] = "TEXT"
    schema.setdefault("Season", "TEXT")
    schema.setdefault("Squad", "TEXT")

    create_table(connection, table_name, schema)

    prepared = df.fillna("N/a")
    upsert_rows(connection, table_name, prepared.to_dict(orient="records"), conflict_keys=["Player", "Season"])


def build_transfers_table(connection, records, table_name: str = "player_transfers") -> None:
    schema = {
        "Player": "TEXT",
        "Season": "TEXT",
        "TransferValue": "TEXT",
        "Currency": "TEXT",
        "SourceUrl": "TEXT",
    }
    create_table(connection, table_name, schema)
    upsert_rows(
        connection,
        table_name,
        (
            {
                "Player": record.player,
                "Season": record.season,
                "TransferValue": record.transfer_value or "N/a",
                "Currency": record.currency or "N/a",
                "SourceUrl": record.url or "N/a",
            }
            for record in records
        ),
        conflict_keys=["Player", "Season"],
    )


def collect(season: str, min_minutes: float) -> None:
    fbref_scraper = FbrefScraper()
    transfers_scraper = FootballTransfersScraper()

    player_stats = fbref_scraper.collect_player_stats(season=season, min_minutes=min_minutes)

    connection = connect()
    build_players_table(connection, player_stats)

    transfer_records = []
    for player in player_stats["Player"].tolist():
        record = transfers_scraper.fetch_transfer_value(player_name=player, season=season)
        transfer_records.append(record)
    build_transfers_table(connection, transfer_records)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", default="2024-2025", help="Season identifier, e.g. 2024-2025")
    parser.add_argument("--min-minutes", type=float, default=90.0, help="Minimum minutes played to include players")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging verbosity",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level))
    HTTP_LOGGER.setLevel(logging.WARNING)
    LOGGER.info("Collecting data for season %s", args.season)
    collect(season=args.season, min_minutes=args.min_minutes)
    LOGGER.info("Data collection finished")


if __name__ == "__main__":
    main()
