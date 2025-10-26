# Premier League Data Engineering & Analytics Toolkit

This project demonstrates how to crawl player statistics for the 2024-2025 Premier League season, enrich the dataset with transfer values, expose the information through REST APIs, and run analytical workflows (aggregations, clustering, PCA visualisation).

## Project Structure

```
.
├── app.py                    # Flask REST API
├── analytics.py              # Statistics, clustering and PCA routines
├── btl/                      # Reusable modules (database + scrapers)
├── data/                     # SQLite database location
├── artifacts/                # Generated CSV files and plots
├── lookup.py                 # CLI client that queries the Flask API
├── requirements.txt          # Python dependencies
└── scripts/
    └── collect_data.py       # Crawl FBref + FootballTransfers and populate SQLite
```

## 1. Data Collection

1. Install dependencies and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Run the collector. By default it targets the 2024-2025 season and filters players with more than 90 minutes played.

   ```bash
   python scripts/collect_data.py --season 2024-2025 --min-minutes 90
   ```

   The script performs the following steps:

   * Downloads the `Standard Stats` table from FBref, converts it into a Pandas `DataFrame`,
     filters players who have accumulated more than 90 minutes, and writes the data into the
     `player_stats` table of `data/premier_league.db`.
   * Iterates through every player and attempts to retrieve their current transfer value from
     [footballtransfers.com](https://www.footballtransfers.com). Transfer valuations are stored in the
     `player_transfers` table.
   * Missing or unavailable values are persisted as `N/a` per the assignment requirements.

### Handling CAPTCHA and Rate Limiting

The scrapers use a shared `HttpClient` that adds:

* Randomised delays between requests.
* Retry logic with exponential backoff for HTTP 429/5xx responses.
* A desktop browser `User-Agent` string.

If the target websites still trigger anti-bot mechanisms you can further harden the collector by:

* Persisting intermediate HTML pages and reusing them when re-running the script.
* Rotating through a pool of proxy servers or VPN endpoints.
* Introducing a headless browser fallback (e.g. Selenium with undetected-chromedriver) for
  pages that require JavaScript rendering or trigger CAPTCHA challenges.

## 2. RESTful API

The Flask application serves two endpoints that read from the SQLite database:

* `GET /api/players?name=<player name>` – returns every record that matches a specific player.
* `GET /api/players?club=<club name>` – returns every player assigned to the requested club.

Both responses include transfer information when available. Start the API with:

```bash
python app.py
```

## 3. Command Line Lookup Client

`lookup.py` is a thin wrapper around the REST API. It prints the response as a table and stores it in a CSV file named after the search key.

```bash
python lookup.py --name "Erling Haaland"
python lookup.py --club "Liverpool"
```

The CLI expects the Flask service to be reachable on `http://localhost:5000`.

## 4. Statistical Analysis & Machine Learning

The `analytics.py` module reads all player statistics from the database and produces:

* Per-team median, mean, and standard deviation for every numeric feature (`artifacts/team_statistics.csv`).
* The best-performing team for each metric (`artifacts/best_team_by_metric.csv`).
* A simple data-driven valuation score for each player (`artifacts/player_valuation_scores.csv`).
* K-Means clustering with elbow and silhouette diagnostics, plus the chosen cluster assignments (`artifacts/player_clusters.csv`).
* PCA scatter plots in 2D and 3D saved into the `artifacts/` folder.

Run the analytics pipeline with:

```bash
python analytics.py
```

## 5. Reporting

All generated CSV files and visualisations under `artifacts/` can be incorporated into the written PDF report alongside any additional commentary or interpretations of the results.
