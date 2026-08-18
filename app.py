import os
import sys
from time import sleep

sys.path.insert(0, os.path.dirname(__file__))


from fetcher.movie_info_fetcher import MovieInfoFetcher
from db.movie_db_handler import MovieDbHandler
import streamlit as st

st.set_page_config(page_title="AI Movie Finder", layout="wide")
st.title("AI Movie Finder")
st.subheader("Find your next favorite movie based on your preferences!")
st.subheader("Please rate the following 3 - 9 criterias on a scale from 1 to 10.")

db = MovieDbHandler()
info_fetcher = MovieInfoFetcher()


# 1. Cache-Dekorator hinzufügen
@st.cache_data(show_spinner="Loading movie details from TMDB...")
def get_cached_movie_info(title: str, year: int = None):
    sleep(0.15)
    return info_fetcher.fetch_details(title=title, year=year)


try:
    available_tags = db.get_all_tag_names()
except Exception:
    st.warning("Please setup the database first!")
    st.stop()


selected_tags = st.multiselect(
    label="Select up to 9 characteristics, vibes, or technical tags:",
    default=["action", "drama", "comedy"],
    options=available_tags,
    max_selections=9,
    placeholder="Type to search (e.g. '007 series', 'space travel', 'disturbing')...",
)

user_preferences = {}

if selected_tags:
    st.divider()
    st.markdown("### 🎛️ Relative Importance Scales (1-10)")

    cols = st.columns(3)
    for i, tag in enumerate(selected_tags):
        with cols[i % 3]:
            user_preferences[tag] = st.slider(
                label=f"Weighting for: **{tag}**",
                min_value=1,
                max_value=10,
                value=5,
                key=f"sl_{tag}",
            )

    if st.button("🚀 Calculate Movie Recommendations", type="primary"):
        with st.spinner("Calculating distances across vector space..."):
            results = db.get_recommendations(user_preferences)

        st.divider()
        st.markdown("### 🏆 Algorithm Output Matrix (Top 20)")
        st.divider()

        if results.empty:
            st.error("Vector convergence returned zero matches for your filters.")
        else:
            for idx, row in results.head(20).reset_index().iterrows():

                # z.B. "Munna bhai M.B.B.S. (2003)
                titel, year = info_fetcher.clean_title(row["title"])

                movie_info = get_cached_movie_info(title=titel, year=year)

                with st.container():
                    c1, c2, c3, c4 = st.columns([0.05, 0.1, 0.55, 0.3])

                    with c1:
                        st.markdown(f"### #{idx+1}")

                    with c2:
                        if movie_info["poster_url"]:
                            st.image(
                                movie_info["poster_url"],
                                width=150,
                            )
                    with c3:

                        st.markdown(f"##### **{row['title']}**")
                        st.caption(f"Genres: {row['genres'].replace('|', ', ')}")

                        st.markdown(f"**Description:** {movie_info['overview']}")

                        if movie_info["imdb_link"]:
                            st.markdown(f"[🎬 IMDb Profil]({movie_info['imdb_link']})")

                        if movie_info["trailer_url"]:
                            st.markdown(f"[▶️ Trailer]({movie_info['trailer_url']})")

                    with c4:
                        match_score_val = row.get(
                            "match_score", row.get("final_score_display", 0)
                        )
                        # print(f"DEBUG: match_score_val = {row}")
                        try:
                            match_pct = float(match_score_val) * 100
                        except Exception:
                            match_pct = 0.0
                        st.metric(label="Vector Match Score", value=f"{match_pct:.1f}%")
                        st.caption(
                            f"⭐ Aggregated Rating: {row.get('mean', 0.0):.2f} / 5"
                        )

                        st.caption(
                            "ℹ️ Note: Film placement is based on weighted genres and customer reviews."
                        )

                    st.divider()


else:
    st.info("💡 Select one or more terms in the search field above to begin.")
