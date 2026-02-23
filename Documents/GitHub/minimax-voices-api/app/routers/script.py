"""Script generation router."""

import os
from typing import Optional

from fastapi import APIRouter, HTTPException
import httpx

router = APIRouter()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


@router.post("")
async def generate_script(
    topic: str,
    tone: str = "neutral",
    duration: int = 60,
    audience: str = "general",
    language: str = "English",
):
    """Generate a video script with scenes and visual direction."""
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")

    if not topic:
        raise HTTPException(status_code=400, detail="Topic is required")

    system_prompt = """You are a professional cinematic video script writer.
Generate structured scripts with scenes, emotions, and music hints.
Return valid JSON with this exact structure:
{
  "title": "...",
  "global_visual_dna": {
    "style": "cinematic",
    "color_grade": "...",
    "lighting_style": "...",
    "camera_language": "...",
    "render_rules": "...",
    "negative_rules": "..."
  },
  "scenes": [
    {
      "text": "...",
      "emotion": "...",
      "music_hint": "...",
      "direction": {
        "environment": "...",
        "subject_action": "...",
        "shot_type": "...",
        "composition": "...",
        "mood": "...",
        "props_or_symbols": "..."
      }
    }
  ]
}"""

    user_prompt = f"""Generate a {duration}-second video script.
Topic: {topic}
Tone: {tone}
Audience: {audience}
Language: {language}

Make it engaging and optimized for voice-over."""

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.7,
                "max_tokens": 2000,
            },
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code, detail="OpenAI API error"
            )

        content = response.json()["choices"][0]["message"]["content"]

        try:
            import json

            script = json.loads(content)
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="Failed to parse script JSON")

        return {
            "title": script.get("title", ""),
            "global_visual_dna": script.get("global_visual_dna", {}),
            "scenes": script.get("scenes", []),
        }
