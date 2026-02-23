"""Image generation router."""

import os

from fastapi import APIRouter, HTTPException
import httpx
import asyncio

router = APIRouter()

FAL_API_KEY = os.getenv("FAL_API_KEY")

# Available image models
MODELS = {
    "flux-pro": "fal-ai/flux-pro",
    "flux-dev": "fal-ai/flux-dev",
    "flux-schnell": "fal-ai/flux-pro/schnell",
    "gpt-image-1": "fal-ai/gpt-image-1/text-to-image",
    "gpt-image-1.5": "fal-ai/gpt-image-1.5",
    "qwen-image": "fal-ai/qwen-image",
    "qwen-image-2512": "fal-ai/qwen-image-2512",
    "imagen-4": "fal-ai/imagen-4",
    "grok-imagine-image": "fal-ai/grok-imagine-image",
}

ASPECT_RATIOS = {
    "16:9": {"width": 1280, "height": 720},
    "1:1": {"width": 1024, "height": 1024},
    "9:16": {"width": 720, "height": 1280},
}


@router.post("")
async def generate_image(
    prompt: str,
    model: str = "flux-pro",
    style: str = "cinematic",
    aspect_ratio: str = "16:9",
    seed: int = None,
):
    """Generate an image from text prompt."""
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")

    if not FAL_API_KEY:
        raise HTTPException(status_code=500, detail="FAL API key not configured")

    fal_model = MODELS.get(model)
    if not fal_model:
        raise HTTPException(
            status_code=400, detail=f"Invalid model. Available: {list(MODELS.keys())}"
        )

    aspect = ASPECT_RATIOS.get(aspect_ratio, ASPECT_RATIOS["16:9"])

    async with httpx.AsyncClient(timeout=120.0) as client:
        # Submit to FAL queue
        submit_response = await client.post(
            f"https://queue.fal.run/{fal_model}",
            json={
                "prompt": prompt,
                "image_size": aspect,
                "seed": seed if seed is not None else -1,
                "num_images": 1,
            },
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
        if not request_id:
            raise HTTPException(status_code=500, detail="Failed to get request ID")

        # Poll for result
        for _ in range(60):  # 60 * 2s = 2 minutes max
            await asyncio.sleep(2)

            status_response = await client.get(
                f"https://queue.fal.run/{fal_model}/requests/{request_id}/status",
                headers={"Authorization": f"Key {FAL_API_KEY}"},
            )

            status = status_response.json().get("status")

            if status == "COMPLETED":
                completion = status_response.json().get("completion", {})
                image_url = completion.get("images", [{}])[0].get(
                    "url"
                ) or completion.get("image", {}).get("url")

                return {
                    "success": True,
                    "model": model,
                    "image_url": image_url,
                    "seed": seed,
                    "aspect_ratio": aspect_ratio,
                }

            elif status == "FAILED":
                raise HTTPException(status_code=500, detail="Image generation failed")

        raise HTTPException(status_code=504, detail="Generation timeout")
