"""
FastAPI AI Capability Server
===========================

Stateless AI generation service.
Input → Output. No retries, no queue, no database.

Endpoints:
- POST /script - Generate video script
- POST /scenes/enrich - Enrich scenes with background music
- POST /tts - Text-to-Speech
- POST /image - Image generation
- POST /music - Music generation
- POST /video - Video generation
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import script, enrich, tts, image, music, video


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    print("Starting AI Capability Server...")
    yield
    print("Shutting down AI Capability Server...")


app = FastAPI(
    title="AI Capability Server",
    description="Stateless AI generation service",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(script.router, prefix="/script", tags=["Script"])
app.include_router(enrich.router, prefix="/scenes", tags=["Scenes"])
app.include_router(tts.router, prefix="/tts", tags=["TTS"])
app.include_router(image.router, prefix="/image", tags=["Image"])
app.include_router(music.router, prefix="/music", tags=["Music"])
app.include_router(video.router, prefix="/video", tags=["Video"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "ai-capability-server"}


@app.get("/models")
async def list_models():
    """List all available models."""
    from app.routers import tts, image, music, video

    return {
        "tts": tts.MODELS,
        "image": image.MODELS,
        "music": music.MODELS,
        "video": video.MODELS,
    }
