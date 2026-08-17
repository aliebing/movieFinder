import sqlite3
import pandas as pd
import os
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import zipfile


class MovieDbHandler:

    def __init__(self, db_path: str = "", is_zip: bool = True) -> None:
        base_dir = os.path.dirname(__file__)

        if db_path == "":
            db_path = os.path.join(base_dir, "moviedoc.db")

        if is_zip == True:
            zip_path = os.path.join(base_dir, "moviedoc.zip")
            if not os.path.isfile(db_path) and os.path.exists(zip_path):
                with zipfile.ZipFile(zip_path, "r") as zip_ref:
                    zip_ref.extractall(base_dir)

        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def get_data(self, query, params=None) -> pd.DataFrame:
        with self._get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=params)

        return df

    def get_all_tag_names(self) -> list[str]:
        query = "SELECT tag FROM genome_tags ORDER BY tag ASC"
        with self._get_connection() as conn:
            df = pd.read_sql_query(query, conn)
            return df["tag"].tolist()

    def get_tables(self) -> pd.DataFrame:
        query = """
            SELECT name AS tabellen_name 
            FROM sqlite_master 
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%';
        """

        with self._get_connection() as conn:
            df = pd.read_sql_query(query, conn)
            return df

    def get_recommendations(self, user_preferences) -> pd.DataFrame:
        """Performs vector calculations directly using structured DB inputs."""
        with self._get_connection() as conn:
            # 1. Load the pre-calculated feature matrix and metadata from DB
            matrix_df = pd.read_sql_query(
                "SELECT * FROM genome_matrix", conn, index_col="movieId"
            )
            movies_df = pd.read_sql_query("SELECT * FROM movies", conn)
            tags_df = pd.read_sql_query("SELECT * FROM genome_tags", conn)

        # 2. Build user vector mapped to the exact matrix column order
        user_vector = np.zeros((1, len(matrix_df.columns)))

        matrix_columns_list = [str(c) for c in matrix_df.columns]
        for tag_name, weight in user_preferences.items():
            matched_tag = tags_df[tags_df["tag"].str.lower() == tag_name.lower()]
            if not matched_tag.empty:
                raw_tag_id = matched_tag["tagId"].iloc[0]
                tag_id_str = str(raw_tag_id)

                # REPARATUR 2: Flexibler Abgleich (sucht nach String oder Zahl)
                if tag_id_str in matrix_columns_list:
                    # Findet den Index, egal ob die Spalte vorher int oder str war
                    col_idx = matrix_columns_list.index(tag_id_str)
                    user_vector[0, col_idx] = float(weight)

        if np.all(user_vector == 0):
            results_df = pd.DataFrame({"movieId": matrix_df.index, "match_score": 0.0})
            final_df = pd.merge(results_df, movies_df, on="movieId", how="inner")
            final_df["final_score"] = final_df["match_score"] * (final_df["mean"] / 5.0)
            return final_df.sort_values(by="final_score", ascending=False)

        # 3. Mathematical Core: Cosine Similarity
        sim_scores = cosine_similarity(user_vector, matrix_df.values)[0]

        # 4. Bind scores back to the pandas DataFrame
        results_df = pd.DataFrame(
            {"movieId": matrix_df.index, "match_score": sim_scores}
        )
        final_df = pd.merge(results_df, movies_df, on="movieId", how="inner")

        # 5. Hybrid Metric: Combine Content Match Vector with Quality Metric (Ratings)
        final_df["final_score"] = final_df["match_score"] * (final_df["mean"] / 5.0)

        return final_df.sort_values(by="final_score", ascending=False)
