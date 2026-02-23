"""TTS router - Text-to-Speech using MiniMax."""

import os

from fastapi import APIRouter, HTTPException
import httpx

router = APIRouter()

MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY")
MINIMAX_API_HOST = os.getenv("MINIMAX_API_HOST", "https://api.minimax.io")
FAL_API_KEY = os.getenv("FAL_API_KEY")

# Available TTS models
MODELS = [
    {"id": "speech-2.8-hd", "name": "Speech 2.8 HD"},
    {"id": "speech-2.8-turbo", "name": "Speech 2.8 Turbo"},
    {"id": "speech-2.6-hd", "name": "Speech 2.6 HD"},
    {"id": "speech-2.6-turbo", "name": "Speech 2.6 Turbo"},
]

# Voice profiles
VOICES = {
    "radiant_girl": {
        "id": "English_radiant_girl",
        "language": "English",
        "gender": "female",
    },
    "narrator": {
        "id": "English_expressive_narrator",
        "language": "English",
        "gender": "male",
    },
    "magnetic_man": {
        "id": "English_magnetic_voiced_man",
        "language": "English",
        "gender": "male",
    },
    "nl_kindhearted_girl": {
        "id": "Dutch_kindhearted_girl",
        "language": "Dutch",
        "gender": "female",
    },
}

VOICE_PROFILES = {
    "narrator_calm": {
        "voice_id": "English_expressive_narrator",
        "speed": 0.95,
        "pitch": -2,
    },
    "narrator_female": {"voice_id": "English_radiant_girl", "speed": 1.0, "pitch": 0},
    "podcast_male": {
        "voice_id": "English_magnetic_voiced_man",
        "speed": 1.0,
        "pitch": 0,
    },
    "podcast_female": {"voice_id": "English_radiant_girl", "speed": 1.02, "pitch": 1},
    "energetic_male": {
        "voice_id": "English_magnetic_voiced_man",
        "speed": 1.1,
        "pitch": 5,
    },
    "energetic_female": {"voice_id": "English_radiant_girl", "speed": 1.1, "pitch": 3},
    "calm_female": {"voice_id": "English_radiant_girl", "speed": 0.92, "pitch": -2},
    "dutch_calm": {"voice_id": "Dutch_kindhearted_girl", "speed": 0.95, "pitch": 0},
}


@router.post("")
async def generate_tts(
    text: str,
    voice: str = "radiant_girl",
    model: str = "speech-2.8-hd",
    speed: float = 1.0,
    vol: float = 1.0,
    pitch: int = 0,
    output_format: str = "url",
):
    """Generate TTS audio from text."""
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")

    if not MINIMAX_API_KEY:
        raise HTTPException(status_code=500, detail="MiniMax API key not configured")

    # Get voice config
    profile = VOICE_PROFILES.get(voice)
    if profile:
        voice_id = profile["voice_id"]
        speed = profile.get("speed", speed)
        pitch = profile.get("pitch", pitch)
    else:
        voice_config = VOICES.get(voice, VOICES["radiant_girl"])
        voice_id = voice_config["id"]

    payload = {
        "model": model,
        "text": text,
        "stream": False,
        "voice_setting": {
            "voice_id": voice_id,
            "speed": max(0.5, min(2.0, speed)),
            "vol": max(0.1, min(2.0, vol)),
            "pitch": max(-12, min(12, pitch)),
        },
        "audio_setting": {
            "sample_rate": 32000,
            "bitrate": 128000,
            "format": "mp3",
            "channel": 1,
        },
        "language_boost": "auto",
        "output_format": output_format,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{MINIMAX_API_HOST}/v1/t2a_v2",
            json=payload,
            headers={
                "Authorization": f"Bearer {MINIMAX_API_KEY}",
                "Content-Type": "application/json",
            },
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code, detail="MiniMax API error"
            )

        data = response.json()

        if data.get("base_resp", {}).get("status_code") != 0:
            raise HTTPException(
                status_code=500,
                detail=data.get("base_resp", {}).get("status_msg", "API error"),
            )

        result = {
            "success": True,
            "model": model,
            "voice": voice_id,
            "audio_format": data.get("extra_info", {}).get("audio_format", "mp3"),
        }

        if output_format == "url":
            result["audio_url"] = data.get("data", {}).get("audio")
        else:
            result["audio_base64"] = data.get("data", {}).get("audio")

        return result


@router.get("/voices")
async def list_voices():
    """List available voices."""
    return {
        "profiles": [{"id": k, **v} for k, v in VOICE_PROFILES.items()],
        "voices": [{"id": k, **v} for k, v in VOICES.items()],
    }
