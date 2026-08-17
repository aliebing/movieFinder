import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from db.movie_db_handler import MovieDbHandler
import streamlit as st

st.set_page_config(page_title="AI Movie Finder", layout="wide")
st.title("AI Movie Finder")
st.subheader("Find your next favorite movie based on your preferences!")
st.subheader("Please rate the following 3 - 9 criterias on a scale from 1 to 10.")

db = MovieDbHandler()

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

    st.divider()

    if st.button("🚀 Calculate Movie Recommendations", type="primary"):
        with st.spinner("Calculating distances across vector space..."):
            results = db.get_recommendations(user_preferences)

        st.markdown("### 🏆 Algorithm Output Matrix (Top 20)")

        if results.empty:
            st.error("Vector convergence returned zero matches for your filters.")
        else:
            for idx, row in results.head(20).reset_index().iterrows():
                with st.container():
                    c1, c2, c3 = st.columns([0.08, 0.62, 0.3])

                    with c1:
                        st.markdown(f"### #{idx+1}")
                    with c2:
                        st.markdown(f"**{row['title']}**")
                        st.caption(f"Genres: {row['genres'].replace('|', ', ')}")
                    with c3:
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

                    st.divider()


else:
    st.info("💡 Select one or more terms in the search field above to begin.")
