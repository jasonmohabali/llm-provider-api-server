"""Video generation router."""

import os

from fastapi import APIRouter, HTTPException
import httpx
import asyncio

router = APIRouter()

FAL_API_KEY = os.getenv("FAL_API_KEY")
MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY")
MINIMAX_API_HOST = os.getenv("MINIMAX_API_HOST", "https://api.minimax.io")

# Available video models
MODELS = {
    # Veo3 (Google)
    "veo3": {"provider": "fal", "fal_id": "fal-ai/veo3", "type": "t2v"},
    "veo3-fast": {"provider": "fal", "fal_id": "fal-ai/veo3/fast", "type": "t2v"},
    "veo3-i2v": {
        "provider": "fal",
        "fal_id": "fal-ai/veo3/image-to-video",
        "type": "i2v",
    },
    # Kling (Kuaishou)
    "kling-3.0-pro-t2v": {
        "provider": "fal",
        "fal_id": "fal-ai/kling-video/v3/pro/text-to-video",
        "type": "t2v",
    },
    "kling-3.0-pro-i2v": {
        "provider": "fal",
        "fal_id": "fal-ai/kling-video/v3/pro/image-to-video",
        "type": "i2v",
    },
    "kling-2.6-pro-t2v": {
        "provider": "fal",
        "fal_id": "fal-ai/kling-video/v2.6/pro/text-to-video",
        "type": "t2v",
    },
    "kling-2.6-pro-i2v": {
        "provider": "fal",
        "fal_id": "fal-ai/kling-video/v2.6/pro/image-to-video",
        "type": "i2v",
    },
    # Sora (OpenAI)
    "sora-2": {
        "provider": "fal",
        "fal_id": "fal-ai/sora-2/text-to-video",
        "type": "t2v",
    },
    "sora-2-pro": {
        "provider": "fal",
        "fal_id": "fal-ai/sora-2/text-to-video/pro",
        "type": "t2v",
    },
    # Hailuo (MiniMax)
    "hailuo-02": {
        "provider": "fal",
        "fal_id": "fal-ai/minimax/hailuo-02/pro/text-to-video",
        "type": "t2v",
    },
    # MiniMax Direct
    "hailuo-2.3": {"provider": "minimax", "type": "t2v"},
    "hailuo-2.3-i2v": {"provider": "minimax", "type": "i2v"},
    "hailuo-2.3-fast": {"provider": "minimax", "type": "i2v"},
    # LTX
    "ltx-video": {"provider": "fal", "fal_id": "fal-ai/ltx-video-v097", "type": "t2v"},
}


@router.post("")
async def generate_video(
    prompt: str = None, image_url: str = None, model: str = "veo3", duration: int = 5
):
    """Generate video from text or image."""
    model_config = MODELS.get(model)
    if not model_config:
        raise HTTPException(
            status_code=400, detail=f"Invalid model. Available: {list(MODELS.keys())}"
        )

    if model_config["type"] == "i2v" and not image_url:
        raise HTTPException(
            status_code=400, detail="image_url required for image-to-video"
        )

    if model_config["type"] == "t2v" and not prompt:
        raise HTTPException(status_code=400, detail="prompt required for text-to-video")

    if model_config["provider"] == "fal":
        return await _generate_fal_video(
            fal_id=model_config["fal_id"],
            model_type=model_config["type"],
            prompt=prompt,
            image_url=image_url,
            duration=duration,
        )
    elif model_config["provider"] == "minimax":
        return await _generate_minimax_video(
            model=model, prompt=prompt, image_url=image_url, duration=duration
        )


async def _generate_fal_video(
    fal_id: str,
    model_type: str,
    prompt: str = None,
    image_url: str = None,
    duration: int = 5,
):
    """Generate video using FAL."""
    if not FAL_API_KEY:
        raise HTTPException(status_code=500, detail="FAL API key not configured")

    request_body = {}
    if model_type == "i2v":
        request_body["image_url"] = image_url
        if prompt:
            request_body["prompt"] = prompt
    else:
        request_body["prompt"] = prompt

    if duration:
        request_body["duration"] = duration

    async with httpx.AsyncClient(timeout=300.0) as client:
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

        # Poll for result (video takes longer)
        for i in range(180):  # 180 * 2s = 6 minutes max
            await asyncio.sleep(2)

            status_response = await client.get(
                f"https://queue.fal.run/{fal_id}/requests/{request_id}/status",
                headers={"Authorization": f"Key {FAL_API_KEY}"},
            )

            status = status_response.json().get("status")

            if status == "COMPLETED":
                completion = status_response.json().get("completion", {})
                video_url = (
                    completion.get("video", {}).get("url")
                    if isinstance(completion.get("video"), dict)
                    else completion.get("video")
                )
                if not video_url:
                    video_url = completion.get("videos", [{}])[0].get("url")

                return {
                    "success": True,
                    "provider": "fal",
                    "model": fal_id,
                    "video_url": video_url,
                    "duration": duration,
                }

            elif status == "FAILED":
                error_msg = status_response.json().get("error", "Unknown error")
                raise HTTPException(
                    status_code=500, detail=f"Video generation failed: {error_msg}"
                )

        raise HTTPException(
            status_code=504, detail="Generation timeout (exceeded 6 minutes)"
        )


async def _generate_minimax_video(
    model: str, prompt: str = None, image_url: str = None, duration: int = 5
):
    """Generate video using MiniMax Direct API."""
    if not MINIMAX_API_KEY:
        raise HTTPException(status_code=500, detail="MiniMax API key not configured")

    # MiniMax video generation endpoint
    payload = {
        "model": "video-01",
        "prompt": prompt or "",
        "image_url": image_url,
        "duration": duration,
    }

    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            f"{MINIMAX_API_HOST}/v1/video_generation",
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

        video_url = data.get("data", {}).get("video")

        return {
            "success": True,
            "provider": "minimax",
            "model": model,
            "video_url": video_url,
            "duration": duration,
        }
