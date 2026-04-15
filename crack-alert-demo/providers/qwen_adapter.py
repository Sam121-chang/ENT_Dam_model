from __future__ import annotations

from typing import Any

from providers.openai_adapter import analyze_image as run_compatible_request


def analyze_image(
    image_bytes: bytes,
    mime_type: str,
    api_key: str,
    api_base_url: str,
    model_name: str,
    timeout: int,
) -> dict[str, Any]:
    result: dict[str, Any] = run_compatible_request(
        image_bytes=image_bytes,
        mime_type=mime_type,
        api_key=api_key,
        api_base_url=api_base_url,
        model_name=model_name,
        timeout=timeout,
    )
    result["model_used"] = model_name
    return result
