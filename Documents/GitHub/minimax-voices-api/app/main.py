"""
FastAPI AI Capability Server
==========================

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
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

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


@app.get("/", response_class=HTMLResponse)
async def root():
    """Root page with links to docs."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Capability Server</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
            h1 { color: #333; }
            .endpoints { background: #f5f5f5; padding: 20px; border-radius: 8px; }
            .endpoint { margin: 10px 0; }
            a { color: #0066cc; text-decoration: none; }
            a:hover { text-decoration: underline; }
            code { background: #e0e0e0; padding: 2px 6px; border-radius: 3px; }
        </style>
    </head>
    <body>
        <h1>AI Capability Server</h1>
        <p>Stateless AI generation service. Input Output.</p>
        
        <div class="endpoints">
            <h2>Available Endpoints</h2>
            <div class="endpoint"><a href="/docs">/docs</a> - API Documentation (Swagger UI)</div>
            <div class="endpoint"><a href="/redoc">/redoc</a> - ReDoc Documentation</div>
            <div class="endpoint"><a href="/health">/health</a> - Health Check</div>
            <div class="endpoint"><a href="/models">/models</a> - Available Models</div>
            <hr>
            <div class="endpoint"><code>POST /script</code> - Generate video script</div>
            <div class="endpoint"><code>POST /scenes/enrich</code> - Enrich scenes with music</div>
            <div class="endpoint"><code>POST /tts</code> - Text-to-Speech</div>
            <div class="endpoint"><code>POST /image</code> - Image generation</div>
            <div class="endpoint"><code>POST /music</code> - Music generation</div>
            <div class="endpoint"><code>POST /video</code> - Video generation</div>
        </div>
    </body>
    </html>
    """


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
