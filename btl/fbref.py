"""Scraper for player statistics from fbref.com."""
from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from typing import Any

import pandas as pd
from bs4 import BeautifulSoup

from .http import HttpClient

LOGGER = logging.getLogger(__name__)

PREMIER_LEAGUE_COMPETITION_ID = 9


class FbrefScraper:
    """Download and parse FBref Premier League data for a season."""

    def __init__(self, client: HttpClient | None = None) -> None:
        self.client = client or HttpClient()

    def premier_league_stats_url(self, season: str) -> str:
        sanitized = season.replace("/", "-")
        return (
            "https://fbref.com/en/comps/"
            f"{PREMIER_LEAGUE_COMPETITION_ID}/{sanitized}/stats/{sanitized}-Premier-League-Stats"
        )

    def fetch_player_table(self, season: str) -> pd.DataFrame:
        """Fetch the "Standard Stats" table for the Premier League season."""
        url = self.premier_league_stats_url(season)
        LOGGER.info("Downloading Premier League stats from %s", url)
        response = self.client.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table", id="stats_standard")
        if table is None:
            raise ValueError("Could not locate the standard stats table on the FBref page")

        df = pd.read_html(str(table), header=[0, 1])[0]
        df.columns = [self._flatten_column(col) for col in df.columns]
        df = df[df["Player"].notna()].copy()
        df = df[df["Player"] != "Player"]
        df = df[~df["Player"].str.contains("Squad Total|Opponent", na=False)]
        df = df.reset_index(drop=True)
        return df

    @staticmethod
    def _flatten_column(column: Iterable[Any]) -> str:
        values = [str(value) for value in column if not str(value).startswith("Unnamed")]
        flat = " ".join(values).strip()
        flat = re.sub(r"\s+", " ", flat)
        return flat

    def filter_by_minutes(self, df: pd.DataFrame, min_minutes: float) -> pd.DataFrame:
        minutes_col_candidates = [
            "Playing Time Min",
            "Playing Time Min 90s",
            "Min",
            "Minutes",
        ]
        for candidate in minutes_col_candidates:
            if candidate in df.columns:
                minutes_col = candidate
                break
        else:
            raise KeyError("Could not determine minutes column in FBref dataset")

        numeric_minutes = pd.to_numeric(df[minutes_col], errors="coerce")
        filtered = df.loc[numeric_minutes > min_minutes].copy()
        filtered[minutes_col] = numeric_minutes[numeric_minutes > min_minutes]
        return filtered

    def collect_player_stats(self, season: str, min_minutes: float = 90.0) -> pd.DataFrame:
        df = self.fetch_player_table(season)
        df = self.filter_by_minutes(df, min_minutes=min_minutes)
        df.insert(0, "Season", season)
        return df


__all__ = ["FbrefScraper"]
