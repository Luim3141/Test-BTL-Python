"""Scraper for player transfer values from footballtransfers.com."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Iterable

from bs4 import BeautifulSoup

from .http import HttpClient

LOGGER = logging.getLogger(__name__)


@dataclass
class TransferRecord:
    player: str
    season: str
    transfer_value: str | None
    currency: str | None
    url: str | None


class FootballTransfersScraper:
    """Retrieve player transfer valuations."""

    def __init__(self, client: HttpClient | None = None) -> None:
        self.client = client or HttpClient()

    def _slugify(self, name: str) -> str:
        slug = name.lower()
        slug = re.sub(r"[^a-z0-9\s-]", "", slug)
        slug = re.sub(r"\s+", "-", slug.strip())
        return slug

    def candidate_urls(self, player_name: str) -> Iterable[str]:
        slug = self._slugify(player_name)
        return [
            f"https://www.footballtransfers.com/en/players/{slug}",
            f"https://www.footballtransfers.com/en/players/{slug}/profile",
        ]

    def fetch_transfer_value(self, player_name: str, season: str) -> TransferRecord:
        for url in self.candidate_urls(player_name):
            try:
                LOGGER.info("Fetching transfer valuation for %s from %s", player_name, url)
                response = self.client.get(url)
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("Failed to download %s: %s", url, exc)
                continue

            value, currency = self._parse_transfer_value(response.text)
            if value:
                return TransferRecord(player=player_name, season=season, transfer_value=value, currency=currency, url=url)

        return TransferRecord(player=player_name, season=season, transfer_value=None, currency=None, url=None)

    @staticmethod
    def _parse_transfer_value(html: str) -> tuple[str | None, str | None]:
        soup = BeautifulSoup(html, "html.parser")
        value_node = soup.select_one("div.player-info__value")
        if not value_node:
            value_node = soup.select_one("div.player-head__value")
        if value_node:
            text = value_node.get_text(strip=True)
            currency_match = re.match(r"([€£$]?)(.*)", text)
            if currency_match:
                currency = currency_match.group(1) or None
                value = currency_match.group(2).strip()
                return value or None, currency
        return None, None


__all__ = ["FootballTransfersScraper", "TransferRecord"]
