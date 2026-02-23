"""Scene enrichment router - adds background music to scenes."""

import os

from fastapi import APIRouter, HTTPException
import httpx

router = APIRouter()

JAMENDO_CLIENT_ID = os.getenv("JAMENDO_CLIENT_ID")
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY")


@router.post("/enrich")
async def enrich_scenes(scenes: list):
    """Enrich scenes with background music."""
    if not scenes:
        raise HTTPException(status_code=400, detail="Scenes required")

    enriched_scenes = []

    for scene in scenes:
        enriched_scene = scene.copy()

        # Check if music is enabled for this scene
        bg_music = scene.get("bgMusic", {})
        if not bg_music or bg_music.get("enabled") is False:
            enriched_scene["music"] = None
            enriched_scenes.append(enriched_scene)
            continue

        # Get track from provider
        try:
            track = await _get_music_track(
                mood=bg_music.get("mood"),
                genre=bg_music.get("genre"),
                duration=bg_music.get("duration"),
            )

            enriched_scene["music"] = {
                "enabled": True,
                "provider": track["provider"],
                "trackId": track["trackId"],
                "trackUrl": track["trackUrl"],
                "title": track["title"],
                "duration": track["duration"],
            }
        except Exception as e:
            enriched_scene["music"] = {"enabled": True, "error": str(e)}

        enriched_scenes.append(enriched_scene)

    return {"scenes": enriched_scenes}


async def _get_music_track(mood: str = None, genre: str = None, duration: int = None):
    """Get a music track from providers."""
    # Try Jamendo first
    if JAMENDO_CLIENT_ID:
        try:
            params = {
                "client_id": JAMENDO_CLIENT_ID,
                "format": "json",
                "limit": "10",
                "order": "popularity_total",
            }
            if mood:
                params["mood"] = mood
            if genre:
                params["genre"] = genre

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://api.jamendo.com/v3.0/tracks/", params=params
                )

                if response.status_code == 200:
                    results = response.json().get("results", [])
                    if results:
                        track = results[0]
                        return {
                            "provider": "jamendo",
                            "trackId": f"jamendo_{track['id']}",
                            "trackUrl": track["audio"],
                            "title": track["name"],
                            "duration": track["duration"],
                        }
        except Exception:
            pass

    # Fallback to Pixabay
    if PIXABAY_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://pixabay.com/api/audio/",
                    params={
                        "key": PIXABAY_API_KEY,
                        "q": mood or genre or "background music",
                        "category": "music",
                        "per_page": "3",
                    },
                )

                if response.status_code == 200:
                    hits = response.json().get("hits", [])
                    if hits:
                        track = hits[0]
                        return {
                            "provider": "pixabay",
                            "trackId": f"pixabay_{track['id']}",
                            "trackUrl": track["audio"],
                            "title": track["tags"].split(",")[0]
                            if track.get("tags")
                            else "Background",
                            "duration": int(track["duration"]),
                        }
        except Exception:
            pass

    raise HTTPException(status_code=500, detail="No music providers available")
