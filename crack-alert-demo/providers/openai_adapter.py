from __future__ import annotations

import base64
import json
from typing import Any

import requests


SYSTEM_PROMPT = """
You are a civil infrastructure crack analysis assistant.
Analyze the image conservatively and return only valid JSON.
Required JSON schema:
{
  "crack_detected": true,
  "risk_level": "Low" | "Medium" | "High",
  "explanation": "1-2 sentences in English",
  "recommendation": "One short English action sentence",
  "intelligence_report": "One professional paragraph in English. Include likely causes, likely risks, and response priorities.",
  "possible_causes": [
    "cause 1",
    "cause 2",
    "cause 3"
  ],
  "potential_risks": [
    "risk 1",
    "risk 2",
    "risk 3"
  ],
  "treatment_options": [
    "option 1",
    "option 2",
    "option 3"
  ],
  "location_hint": {
    "mode": "bbox" | "region" | "none",
    "x": 0-100,
    "y": 0-100,
    "width": 0-100,
    "height": 0-100,
    "description": "short English phrase"
  }
}

Rules:
- If no clear crack is visible, set crack_detected to false and location_hint.mode to "none".
- Use bbox percentages only when you can estimate a region.
- Keep the explanation factual and concise.
- The intelligence_report should read like a monitoring center assessment note.
- possible_causes, potential_risks, and treatment_options must each contain exactly 3 short items.
- Do not include markdown fences or extra commentary.
""".strip()


def _extract_message_content(data: dict[str, Any]) -> str:
    choices = data.get("choices") or []
    if not choices:
        raise ValueError("No choices returned by the upstream API.")

    message = choices[0].get("message") or {}
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = [
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and part.get("type") in {"text", "output_text"}
        ]
        return "".join(text_parts).strip()
    raise ValueError("Unsupported message content format.")


def _coerce_json_text(raw_text: str) -> str:
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3:
            text = "\n".join(lines[1:-1]).strip()
    return text


def analyze_image(
    image_bytes: bytes,
    mime_type: str,
    api_key: str,
    api_base_url: str,
    model_name: str,
    timeout: int,
) -> dict[str, Any]:
    image_data_url = (
        f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('utf-8')}"
    )
    payload = {
        "model": model_name,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Determine whether the image shows a structural crack. "
                            "Return the required JSON only."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": image_data_url},
                    },
                ],
            },
        ],
    }
    response = requests.post(
        f"{api_base_url}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()
    raw_text = _extract_message_content(response.json())
    parsed = json.loads(_coerce_json_text(raw_text))
    parsed["model_used"] = model_name
    return parsed
