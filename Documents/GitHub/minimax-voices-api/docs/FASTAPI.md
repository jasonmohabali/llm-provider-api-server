# FastAPI AI Capability Server

Stateless AI generation service. Input → Output. No retries, no queue, no database.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run server
python -m uvicorn app.main:app --reload

# Or with custom port
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Environment Variables

Copy `.env.example` to `.env` and fill in your API keys:

```env
MINIMAX_API_KEY=your_minimax_api_key
FAL_API_KEY=your_fal_api_key
OPENAI_API_KEY=your_openai_api_key
```

## Endpoints

### POST /script

Generate a video script with scenes and visual direction.

```bash
curl -X POST "http://localhost:8000/script?topic=AI%20future&tone=neutral&duration=60" \
  -H "Content-Type: application/json"
```

**Parameters:**
- `topic` (required) - Video topic
- `tone` (optional) - neutral, inspiring, dramatic, etc.
- `duration` (optional, default: 60) - Video duration in seconds
- `audience` (optional) - Target audience
- `language` (optional, default: English)

**Response:**
```json
{
  "title": "...",
  "global_visual_dna": {...},
  "scenes": [...]
}
```

### POST /scenes/enrich

Enrich scenes with background music.

```bash
curl -X POST "http://localhost:8000/scenes/enrich" \
  -H "Content-Type: application/json" \
  -d '{"scenes": [{"text": "...", "bgMusic": {"enabled": true, "mood": "upbeat"}}]}'
```

### POST /tts

Text-to-Speech generation.

```bash
curl -X POST "http://localhost:8000/tts?text=Hello%20world&voice=radiant_girl&model=speech-2.8-hd"
```

**Parameters:**
- `text` (required) - Text to speak
- `voice` (optional) - Voice profile ID
- `model` (optional) - TTS model
- `speed` (optional, default: 1.0)
- `pitch` (optional, default: 0)
- `output_format` (optional, default: url) - url or base64

### POST /image

Image generation via FAL.ai.

```bash
curl -X POST "http://localhost:8000/image?prompt=A%20beautiful%20sunset&model=flux-pro"
```

**Parameters:**
- `prompt` (required) - Image description
- `model` (optional) - Image model (flux-pro, gpt-image-1, qwen-image, imagen-4)
- `style` (optional) - cinematic, realistic, anime, etc.
- `aspect_ratio` (optional, default: 16:9) - 16:9, 1:1, 9:16
- `seed` (optional) - Random seed for reproducibility

### POST /music

Music generation.

```bash
curl -X POST "http://localhost:8000/music?prompt=upbeat%20pop&model=music-2.5"
```

**Parameters:**
- `lyrics` (optional) - Song lyrics
- `prompt` (optional) - Music description
- `model` (optional) - music-2.5, sonauto-v2
- `duration` (optional, default: 30)
- `output_format` (optional, default: url)

### POST /video

Video generation.

```bash
curl -X POST "http://localhost:8000/video?prompt=A%20cat%20running&model=veo3"
```

**Parameters:**
- `prompt` (required for text-to-video) - Video description
- `image_url` (required for image-to-video) - Input image URL
- `model` (optional, default: veo3) - Video model
- `duration` (optional, default: 5)

**Available Video Models:**
- `veo3` - Google Veo 3 (T2V)
- `veo3-fast` - Veo 3 Fast
- `kling-3.0-pro-t2v` - Kling 3.0 Pro (T2V)
- `kling-3.0-pro-i2v` - Kling 3.0 Pro (I2V)
- `sora-2` - OpenAI Sora 2 (T2V)
- `hailuo-02` - MiniMax Hailuo 02 (T2V)
- `hailuo-2.3` - MiniMax Hailuo 2.3 (T2V, Direct)
- `ltx-video` - LTX Video (T2V)

### GET /health

Health check endpoint.

### GET /models

List all available models.

## Architecture

```
app/
  main.py          # FastAPI entry point
  routers/
    script.py      # Script generation
    enrich.py      # Scene enrichment
    tts.py         # Text-to-Speech
    image.py       # Image generation
    music.py       # Music generation
    video.py       # Video generation
  services/        # Provider integrations
  models/          # Pydantic models
```

## Stateless Design

This server is designed to be **stateless**:
- No database
- No job queue
- No retries (handled by orchestrator)
- No state persistence

**Each request is independent.** The orchestrator handles:
- Retries on failure
- Job status tracking
- Webhook callbacks
- Queue management

## Deployment

### Railway
```bash
railway init
railway deploy
```

### Render
```bash
render.yaml included - just connect to GitHub
```

### Docker
```bash
docker build -t ai-capability-server .
docker run -p 8000:8000 --env-file .env ai-capability-server
```

### VPS with Gunicorn
```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```
