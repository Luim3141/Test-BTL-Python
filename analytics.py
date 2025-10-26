"""Analytical workflows for the collected Premier League dataset."""
from __future__ import annotations

import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from btl.database import connect

LOGGER = logging.getLogger(__name__)

ARTIFACTS_DIR = Path("artifacts")
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


def load_player_dataframe() -> pd.DataFrame:
    connection = connect()
    df = pd.read_sql_query("SELECT * FROM player_stats", connection)
    df = df.replace({"N/a": np.nan})
    return df


def get_numeric_features(df: pd.DataFrame) -> pd.DataFrame:
    numeric_df = df.copy()
    for column in numeric_df.columns:
        if column in {"Player", "Nation", "Pos", "Squad", "Comp", "Season", "Birth Year"}:
            continue
        numeric_df[column] = pd.to_numeric(numeric_df[column], errors="coerce")
    return numeric_df.select_dtypes(include=["number"]).drop(columns=["Rk"], errors="ignore")


def team_statistics(df: pd.DataFrame) -> pd.DataFrame:
    numeric_df = get_numeric_features(df)
    numeric_df["Squad"] = df["Squad"]
    grouped = numeric_df.groupby("Squad")
    summary = grouped.agg(["median", "mean", "std"]).transpose()
    summary = summary.swaplevel().sort_index()
    output_path = ARTIFACTS_DIR / "team_statistics.csv"
    summary.to_csv(output_path)
    LOGGER.info("Saved team statistics to %s", output_path)
    return summary


def best_team_by_metric(df: pd.DataFrame) -> pd.DataFrame:
    numeric_df = get_numeric_features(df)
    numeric_df["Squad"] = df["Squad"]
    grouped = numeric_df.groupby("Squad").mean(numeric_only=True)
    best = grouped.idxmax()
    output = pd.DataFrame({"BestTeam": best})
    output_path = ARTIFACTS_DIR / "best_team_by_metric.csv"
    output.to_csv(output_path)
    LOGGER.info("Saved best team by metric to %s", output_path)
    return output


def recommend_player_valuation(df: pd.DataFrame) -> pd.Series:
    numeric_df = get_numeric_features(df)
    scaler = StandardScaler()
    scaled = scaler.fit_transform(numeric_df.fillna(0))
    weights = np.mean(scaled, axis=0)
    valuation_score = scaled @ weights
    recommendation = pd.Series(valuation_score, index=df["Player"], name="valuation_score")
    output_path = ARTIFACTS_DIR / "player_valuation_scores.csv"
    recommendation.to_csv(output_path, header=True)
    LOGGER.info("Saved valuation scores to %s", output_path)
    return recommendation


def run_kmeans(df: pd.DataFrame, k_values: range = range(2, 11)) -> tuple[int, pd.DataFrame]:
    numeric_df = get_numeric_features(df)
    scaled = StandardScaler().fit_transform(numeric_df.fillna(0))

    inertias: list[float] = []
    silhouettes: list[float] = []
    best_k = None
    best_silhouette = -np.inf

    for k in k_values:
        model = KMeans(n_clusters=k, n_init="auto", random_state=42)
        labels = model.fit_predict(scaled)
        inertias.append(model.inertia_)
        if len(set(labels)) > 1:
            score = silhouette_score(scaled, labels)
        else:
            score = float("nan")
        silhouettes.append(score)
        if not np.isnan(score) and score > best_silhouette:
            best_silhouette = score
            best_k = k

    plot_elbow(k_values, inertias)
    plot_silhouette(k_values, silhouettes)

    if best_k is None:
        best_k = k_values.start

    final_model = KMeans(n_clusters=best_k, n_init="auto", random_state=42)
    labels = final_model.fit_predict(scaled)
    clustered_df = df.copy()
    clustered_df["Cluster"] = labels
    output_path = ARTIFACTS_DIR / "player_clusters.csv"
    clustered_df.to_csv(output_path, index=False)
    LOGGER.info("Saved cluster assignments to %s", output_path)
    return best_k, clustered_df


def plot_elbow(k_values: range, inertias: list[float]) -> None:
    plt.figure(figsize=(8, 5))
    plt.plot(list(k_values), inertias, marker="o")
    plt.title("Elbow Method for Optimal k")
    plt.xlabel("Number of clusters (k)")
    plt.ylabel("Inertia")
    path = ARTIFACTS_DIR / "kmeans_elbow.png"
    plt.savefig(path, bbox_inches="tight")
    plt.close()
    LOGGER.info("Saved elbow plot to %s", path)


def plot_silhouette(k_values: range, silhouettes: list[float]) -> None:
    plt.figure(figsize=(8, 5))
    plt.plot(list(k_values), silhouettes, marker="o")
    plt.title("Silhouette Scores")
    plt.xlabel("Number of clusters (k)")
    plt.ylabel("Silhouette score")
    path = ARTIFACTS_DIR / "kmeans_silhouette.png"
    plt.savefig(path, bbox_inches="tight")
    plt.close()
    LOGGER.info("Saved silhouette plot to %s", path)


def pca_visualisations(df: pd.DataFrame) -> None:
    numeric_df = get_numeric_features(df)
    scaled = StandardScaler().fit_transform(numeric_df.fillna(0))

    pca_2d = PCA(n_components=2, random_state=42)
    coords_2d = pca_2d.fit_transform(scaled)
    plot_pca(coords_2d, df["Player"], "pca_2d.png", dims=2)

    pca_3d = PCA(n_components=3, random_state=42)
    coords_3d = pca_3d.fit_transform(scaled)
    plot_pca(coords_3d, df["Player"], "pca_3d.png", dims=3)


def plot_pca(coords: np.ndarray, labels: pd.Series, filename: str, dims: int) -> None:
    path = ARTIFACTS_DIR / filename
    if dims == 2:
        plt.figure(figsize=(8, 6))
        plt.scatter(coords[:, 0], coords[:, 1], alpha=0.7)
        plt.xlabel("PC1")
        plt.ylabel("PC2")
        plt.title("PCA 2D Projection")
        plt.savefig(path, bbox_inches="tight")
        plt.close()
    elif dims == 3:
        from mpl_toolkits.mplot3d import Axes3D  # noqa: F401 - needed for 3D projection

        fig = plt.figure(figsize=(8, 6))
        ax = fig.add_subplot(111, projection="3d")
        ax.scatter(coords[:, 0], coords[:, 1], coords[:, 2], alpha=0.7)
        ax.set_xlabel("PC1")
        ax.set_ylabel("PC2")
        ax.set_zlabel("PC3")
        ax.set_title("PCA 3D Projection")
        plt.savefig(path, bbox_inches="tight")
        plt.close()
    LOGGER.info("Saved PCA plot to %s", path)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    df = load_player_dataframe()
    if df.empty:
        LOGGER.error("No player data found. Please run scripts/collect_data.py first")
        return

    team_statistics(df)
    best_team_by_metric(df)
    recommend_player_valuation(df)
    best_k, clustered_df = run_kmeans(df)
    LOGGER.info("Recommended number of clusters based on silhouette score: %s", best_k)
    pca_visualisations(clustered_df)


if __name__ == "__main__":
    main()
