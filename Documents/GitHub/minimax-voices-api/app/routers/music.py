"""Music generation router."""

import os

from fastapi import APIRouter, HTTPException
import httpx
import asyncio

router = APIRouter()

MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY")
MINIMAX_API_HOST = os.getenv("MINIMAX_API_HOST", "https://api.minimax.io")
FAL_API_KEY = os.getenv("FAL_API_KEY")

# Available music models
MODELS = {
    "music-2.5": {"provider": "minimax"},
    "music-02": {"provider": "minimax"},
    "sonauto-v2": {"provider": "fal", "fal_id": "sonauto/v2/text-to-music"},
}


@router.post("")
async def generate_music(
    lyrics: str = None,
    prompt: str = None,
    model: str = "music-2.5",
    duration: int = 30,
    output_format: str = "url",
):
    """Generate music from lyrics or prompt."""
    model_config = MODELS.get(model)
    if not model_config:
        raise HTTPException(
            status_code=400, detail=f"Invalid model. Available: {list(MODELS.keys())}"
        )

    if model_config["provider"] == "minimax":
        return await _generate_minimax_music(
            model=model, lyrics=lyrics, prompt=prompt, output_format=output_format
        )
    elif model_config["provider"] == "fal":
        return await _generate_fal_music(
            fal_id=model_config["fal_id"], lyrics=lyrics, prompt=prompt
        )


async def _generate_minimax_music(
    model: str, lyrics: str = None, prompt: str = None, output_format: str = "url"
):
    """Generate music using MiniMax API."""
    if not MINIMAX_API_KEY:
        raise HTTPException(status_code=500, detail="MiniMax API key not configured")

    if not lyrics and not prompt:
        raise HTTPException(status_code=400, detail="Either lyrics or prompt required")

    payload = {
        "model": model,
        "prompt": prompt or "",
        "lyrics": lyrics or "",
        "stream": False,
        "audio_setting": {"sample_rate": 44100, "bitrate": 256000, "format": "mp3"},
        "output_format": output_format,
    }

    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(
            f"{MINIMAX_API_HOST}/v1/music_generation",
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
            "audio_format": "mp3",
        }

        if output_format == "url":
            result["music_url"] = data.get("data", {}).get("audio")
        else:
            result["music_base64"] = data.get("data", {}).get("audio")

        return result


async def _generate_fal_music(fal_id: str, lyrics: str = None, prompt: str = None):
    """Generate music using FAL (Sonauto)."""
    if not FAL_API_KEY:
        raise HTTPException(status_code=500, detail="FAL API key not configured")

    request_body = {}
    if prompt:
        request_body["prompt"] = prompt
    if lyrics:
        request_body["lyrics"] = lyrics

    async with httpx.AsyncClient(timeout=180.0) as client:
        # Submit to FAL queue
        submit_response = await client.post(
            f"https://queue.fal.run/{fal_id}",
            json=request_body,
            headers={
                "Authorization": f"Key {FAL_API_KEY}",
                "Content-Type": "application/json",
            },
        )

        if submit_response.status_code != 200:
            raise HTTPException(
                status_code=submit_response.status_code, detail="FAL submission failed"
            )

        request_id = submit_response.json().get("request_id")

        # Poll for result
        for _ in range(90):
            await asyncio.sleep(2)

            status_response = await client.get(
                f"https://queue.fal.run/{fal_id}/requests/{request_id}/status",
                headers={"Authorization": f"Key {FAL_API_KEY}"},
            )

            status = status_response.json().get("status")

            if status == "COMPLETED":
                completion = status_response.json().get("completion", {})
                audio_url = (
                    completion.get("audio", {}).get("url")
                    if isinstance(completion.get("audio"), dict)
                    else completion.get("audio")
                )

                return {
                    "success": True,
                    "provider": "fal",
                    "model": fal_id,
                    "music_url": audio_url,
                }

            elif status == "FAILED":
                raise HTTPException(status_code=500, detail="Music generation failed")

        raise HTTPException(status_code=504, detail="Generation timeout")
