import requests
from typing import Dict, Any, Optional


class MovieInfoFetcher:
    def __init__(self, api_key: str = "8a6e5bee8b59e765a08703cf6d18737e"):
        self.api_key: str = api_key
        self.base_url: str = "https://api.themoviedb.org/3"
        self.image_base_url: str = "https://image.tmdb.org/t/p/w185"

    def clean_title(self, title: str) -> tuple[str, int | None]:
        search_title = title
        year = None

        if "(" in search_title and search_title.endswith(")"):
            parts = search_title.rsplit("(", 1)
            search_title = parts[0].strip()
            year_str = parts[1].replace(")", "").strip()
            if year_str.isdigit():
                year = int(year_str)
        if "(" in title and ")" in title:
            parts = title.rsplit("(", 1)

        return search_title, year

    def fetch_details(self, title: str, year: Optional[int] = None) -> Dict[str, Any]:
        default_data = {
            "poster_url": "",
            "overview": "Keine Beschreibung verfügbar.",
            "imdb_link": None,
            "trailer_url": None,
        }

        # DEBUG 1: Prüfen ob der Key eingetragen ist
        if not self.api_key or self.api_key == "DEIN_TMDB_API_KEY":
            print("⚠️ DEBUG: Kein gültiger API-Key hinterlegt!")
            return default_data

        try:
            # 1. Film suchen
            search_url = f"{self.base_url}/search/movie"
            params = {"api_key": self.api_key, "query": title}
            if year:
                params["primary_release_year"] = year

            response = requests.get(search_url, params=params)

            # DEBUG 2: Server-Antwort prüfen (z.B. 401 Unauthorized bei falschem Key)
            if response.status_code != 200:
                print(
                    f"⚠️ DEBUG: API-Fehler {response.status_code} bei Film '{title}'. Antwort: {response.text}"
                )
                return default_data

            try:
                response_json = response.json()
            except Exception as json_err:
                print(
                    f"❌ JSON-Parsing-Fehler bei Film '{title}'. Der Server hat kein JSON gesendet!"
                )
                print(f"📄 Server-Antwort (erste 200 Zeichen): {response.text[:200]}")
                return default_data

            if not response_json.get("results"):
                print(f"ℹ️ DEBUG: Film '{title}' wurde bei TMDB nicht gefunden.")
                return default_data

            # REPARATUR: results ist eine LISTE. Wir müssen den ERSTEN Eintrag holen!
            first_result = response_json["results"][0]
            movie_id = first_result["id"]

            # 2. Details & Videos (Trailer) abrufen
            detail_url = f"{self.base_url}/movie/{movie_id}"
            detail_params = {"api_key": self.api_key, "append_to_response": "videos"}
            details_response = requests.get(detail_url, params=detail_params)

            # WICHTIG: Wenn hier z.B. ein 429 oder 404 kommt, fangen wir es sauber ab!
            if details_response.status_code != 200:
                print(
                    f"⚠️ DEBUG: Fehler {details_response.status_code} beim Abrufen der Details für ID {movie_id}. Antwort: {details_response.text}"
                )
                return default_data

            try:
                details = details_response.json()
            except Exception as json_err:
                print(
                    f"❌ Fehler beim Parsen der Detail-Antwort für ID {movie_id}: {json_err}. Inhalt: {details_response.text[:100]}"
                )
                return default_data

            # Daten zusammenbauen
            if details.get("poster_path"):
                default_data["poster_url"] = (
                    f"{self.image_base_url}{details['poster_path']}"
                )

            if details.get("overview"):
                default_data["overview"] = details["overview"]

            if details.get("imdb_id"):
                default_data["imdb_link"] = (
                    f"https://imdb.com/title/{details['imdb_id']}"
                )

            videos = details.get("videos", {}).get("results", [])
            for video in videos:
                if video.get("site") == "YouTube" and video.get("type") == "Trailer":
                    # REPARATUR: Fehlenden Slash und Standard-Watch-Format bei YouTube hinzugefügt
                    default_data["trailer_url"] = (
                        f"https://youtube.com/watch?v={video['key']}"
                    )
                    break

            return default_data

        except Exception as e:
            # DEBUG 3: Den echten Python-Fehler im Terminal ausgeben lassen
            print(
                f"❌ CRITICAL DEBUG: Ein unerwarteter Fehler ist aufgetreten: {str(e)}"
            )
            return default_data
