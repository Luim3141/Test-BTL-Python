"""Flask application exposing RESTful endpoints for player statistics."""
from __future__ import annotations

import logging
import sqlite3
from typing import Iterable

from flask import Flask, jsonify, request

from btl.database import connect

LOGGER = logging.getLogger(__name__)


def row_to_dict(row) -> dict:
    return {key: row[key] for key in row.keys()}


def query_players_by_name(name: str) -> list[dict]:
    connection = connect()
    try:
        rows = connection.execute(
            "SELECT * FROM player_stats WHERE LOWER(Player) = LOWER(?)",
            (name,),
        ).fetchall()
    except sqlite3.OperationalError:
        LOGGER.warning("player_stats table not initialised")
        return []
    return [row_to_dict(row) for row in rows]


def query_players_by_club(club: str) -> list[dict]:
    connection = connect()
    try:
        rows = connection.execute(
            "SELECT * FROM player_stats WHERE LOWER(Squad) = LOWER(?)",
            (club,),
        ).fetchall()
    except sqlite3.OperationalError:
        LOGGER.warning("player_stats table not initialised")
        return []
    return [row_to_dict(row) for row in rows]


def query_transfers_by_players(players: Iterable[str]) -> dict[str, dict]:
    players = list(players)
    if not players:
        return {}

    connection = connect()
    placeholders = ",".join(["?"] * len(players))
    try:
        rows = connection.execute(
            f"SELECT * FROM player_transfers WHERE Player IN ({placeholders})",
            players,
        ).fetchall()
    except sqlite3.OperationalError:
        LOGGER.warning("player_transfers table not initialised")
        return {}
    return {row["Player"]: row_to_dict(row) for row in rows}


def create_app() -> Flask:
    app = Flask(__name__)

    @app.route("/api/players")
    def players_endpoint():
        name = request.args.get("name")
        club = request.args.get("club")
        if not name and not club:
            return jsonify({"error": "Please provide either name or club query parameter"}), 400

        if name:
            data = query_players_by_name(name)
        else:
            data = query_players_by_club(club or "")

        if not data:
            return jsonify([])

        transfer_data = query_transfers_by_players({row["Player"] for row in data})
        for row in data:
            transfer = transfer_data.get(row["Player"])
            if transfer:
                row["Transfer"] = transfer
        return jsonify(data)

    return app


app = create_app()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run(host="0.0.0.0", port=5000, debug=False)
