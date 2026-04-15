# Crack Alert Demo

Professional web demo for image-based crack screening and response guidance.

## Overview
This project provides a local Flask web application for structural crack screening. A user uploads a single image, and the system returns:

- crack / no-crack judgement
- low / medium / high risk level
- short recommendation
- long-form intelligence report
- three likely causes
- three potential risks
- three treatment options
- annotated image output
- model name used for the final result

The application is designed for demonstration, presentation, and prototype validation. It focuses on stable end-to-end flow rather than engineering-grade defect diagnosis.

## Features
- Single-image upload workflow
- OpenAI-compatible API integration
- Fallback model sequence
- Structured JSON normalization
- Monitoring-center style UI
- Annotated image generation
- Temporary file cleanup
- Local development setup with `.env`

## Project Structure
```text
crack-alert-demo/
├── .env.example
├── .gitignore
├── README.md
├── app.py
├── config.py
├── docs/
│   └── system-design-zh-cn.md
├── providers/
│   ├── __init__.py
│   ├── gemini_adapter.py
│   ├── openai_adapter.py
│   └── qwen_adapter.py
├── requirements.txt
├── services/
│   ├── __init__.py
│   ├── analyze_service.py
│   └── annotation_service.py
├── static/
│   └── style.css
├── temp/
│   └── .gitkeep
└── templates/
    └── index.html
```

## Requirements
- Python 3.11+
- A valid API key for an OpenAI-compatible gateway
- Internet access for upstream model calls

## Quick Start
1. Open a terminal in the project folder:
   ```bash
   cd crack-alert-demo
   ```
2. Create a virtual environment:
   ```bash
   python3 -m venv .venv
   ```
3. Activate it:
   ```bash
   source .venv/bin/activate
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Create a local environment file:
   ```bash
   cp .env.example .env
   ```
6. Edit `.env` and add your own API key and model settings.
7. Start the app:
   ```bash
   python3 app.py
   ```
8. Open:
   [http://127.0.0.1:5001](http://127.0.0.1:5001)

## Environment Variables
Example `.env`:

```env
API_KEY=your_own_api_key_here
API_BASE_URL=https://api.jiekou.ai/openai
PRIMARY_MODEL=gpt-4.1-mini
FALLBACK_MODEL_1=gemini-2.5-flash
FALLBACK_MODEL_2=gpt-4.1
REQUEST_TIMEOUT=45
```

### Notes
- Never commit `.env`.
- Each teammate should use their own API key.
- If your gateway uses different model IDs, update only the `.env` file.
- The code expects an OpenAI-compatible `chat/completions` image API.

## Running on Another Teammate's Computer
To run the project on another computer:

1. Send the folder without `.env` and without `.venv`.
2. The teammate installs Python 3.11+.
3. The teammate creates a new virtual environment.
4. The teammate installs dependencies with `pip install -r requirements.txt`.
5. The teammate copies `.env.example` to `.env`.
6. The teammate pastes their own API key into `.env`.
7. The teammate starts the app with `python3 app.py`.

The Chinese system design document is available here:
[docs/system-design-zh-cn.md](/Users/sammr.chang/Desktop/西浦课内/ENT/crack-alert-demo/docs/system-design-zh-cn.md)

## API Endpoints
### `GET /health`
Returns application readiness and configuration validation status.

Example:
```json
{
  "status": "ok",
  "errors": []
}
```

### `POST /analyze`
Accepts one image file through multipart form-data.

Field:
- `image`

Supported types:
- `.jpg`
- `.jpeg`
- `.png`

Example response:
```json
{
  "annotated_image_url": "/temp/example_annotated.png",
  "crack_detected": true,
  "explanation": "A visible crack-like feature is present on the surface.",
  "intelligence_report": "A visible crack indication is present. The likely contributing factors include localized tensile stress, moisture exposure, and material aging. The main concerns are crack propagation, reduced durability, and possible serviceability decline. Recommended actions include urgent inspection, short-cycle monitoring, and repair planning.",
  "judgement": "Crack Detected",
  "location_hint": {
    "description": "lower-right region",
    "height": 18,
    "mode": "bbox",
    "width": 28,
    "x": 58,
    "y": 62
  },
  "model_used": "gpt-4.1-mini",
  "original_image_url": "/temp/example_original.png",
  "possible_causes": [
    "Localized tensile stress may have opened the surface crack.",
    "Moisture and thermal cycling may be accelerating deterioration.",
    "Material aging may be weakening the affected area."
  ],
  "potential_risks": [
    "Crack propagation may expand under repeated loading.",
    "Water ingress may reduce durability over time.",
    "Local serviceability may degrade without intervention."
  ],
  "recommendation": "Perform urgent on-site inspection and safety assessment.",
  "risk_level": "High",
  "treatment_options": [
    "Arrange urgent on-site engineering inspection.",
    "Implement short-cycle monitoring and re-imaging.",
    "Prepare localized sealing or reinforcement after confirmation."
  ]
}
```

## Fallback Model Order
The app tries models in this order:

1. `PRIMARY_MODEL`
2. `FALLBACK_MODEL_1`
3. `FALLBACK_MODEL_2`

If one model fails or returns an invalid structure, the app automatically switches to the next model.

## Security
- API keys stay on the server side only.
- `.env` is ignored by Git.
- The browser never receives the raw API key.
- Temporary images are written to `temp/` and cleaned automatically.

## Packaging Checklist
Before sending the project to another teammate:

- keep `.env.example`
- do not include `.env`
- do not include `.venv`
- do not include `__pycache__`
- keep `temp/.gitkeep`
- keep `docs/system-design-zh-cn.md`

## License
For coursework / internal demo use.
