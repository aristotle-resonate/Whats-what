import base64

import httpx

from app.collectors.base import BaseCollector, MentionData
from app.collectors.cities import CITY_CONFIG
from app.config import settings

CITY_SEARCH_TERMS: dict[str, str] = {
    "austin": "Austin Texas",
    "dallas": "Dallas Texas",
    "san-antonio": "San Antonio Texas",
    "new-york": "New York",
    "los-angeles": "Los Angeles",
}


class SpotifyCollector(BaseCollector):
    source_name = "spotify"

    async def collect(self, city: str) -> list[MentionData]:
        if not settings.spotify_client_id or not settings.spotify_client_secret:
            return []

        search_term = CITY_SEARCH_TERMS.get(city, city)
        credentials = base64.b64encode(
            f"{settings.spotify_client_id}:{settings.spotify_client_secret}".encode()
        ).decode()

        async with httpx.AsyncClient() as client:
            # Get token
            token_resp = await client.post(
                "https://accounts.spotify.com/api/token",
                data={"grant_type": "client_credentials"},
                headers={"Authorization": f"Basic {credentials}"},
            )
            token_resp.raise_for_status()
            token = token_resp.json()["access_token"]

            # Search artists
            search_resp = await client.get(
                "https://api.spotify.com/v1/search",
                params={
                    "q": f"genre:pop city:{search_term}",
                    "type": "artist",
                    "market": "US",
                    "limit": 50,
                },
                headers={"Authorization": f"Bearer {token}"},
            )
            search_resp.raise_for_status()
            artists = search_resp.json().get("artists", {}).get("items", [])

        results: list[MentionData] = []
        for artist in artists:
            popularity = artist.get("popularity", 0)
            if popularity < 20:
                continue

            genres = artist.get("genres", [])
            snippet = f"Genres: {', '.join(genres[:3])}" if genres else None

            results.append(
                MentionData(
                    entity_name=artist["name"][:255],
                    entity_type="artist",
                    category="music",
                    content_snippet=snippet,
                    url=artist.get("external_urls", {}).get("spotify"),
                    mention_count=popularity,
                    sentiment_score=None,
                    published_at=None,
                )
            )

        return results
