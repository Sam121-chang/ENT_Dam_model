from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any, Callable

from PIL import Image
from PIL import UnidentifiedImageError
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from config import Config
from providers import gemini_adapter, openai_adapter, qwen_adapter
from services.annotation_service import create_annotation


class AnalysisError(Exception):
    pass


PROVIDERS: list[tuple[str, Callable[..., dict[str, Any]], str]] = [
    ("openai", openai_adapter.analyze_image, Config.PRIMARY_MODEL),
    ("gemini", gemini_adapter.analyze_image, Config.FALLBACK_MODEL_1),
    ("qwen", qwen_adapter.analyze_image, Config.FALLBACK_MODEL_2),
]

ALLOWED_MIME_TYPES = {"image/jpeg", "image/png"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_EXTENSIONS


def cleanup_temp_files(max_age_seconds: int = 1800) -> None:
    now = time.time()
    for path in Config.TEMP_DIR.iterdir():
        if path.name == ".gitkeep" or not path.is_file():
            continue
        if now - path.stat().st_mtime > max_age_seconds:
            path.unlink(missing_ok=True)


def _normalize_risk_level(value: Any, crack_detected: bool) -> str:
    text = str(value or "").strip().lower()
    mapping = {"low": "Low", "medium": "Medium", "high": "High"}
    if text in mapping:
        return mapping[text]
    return "Low" if not crack_detected else "Medium"


def _normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value or "").strip().lower()
    if text in {"true", "yes", "1", "detected", "crack"}:
        return True
    if text in {"false", "no", "0", "none", "no crack"}:
        return False
    return False


def _normalize_recommendation(risk_level: str) -> str:
    recommendations = {
        "Low": "Continue routine monitoring.",
        "Medium": "Schedule manual inspection and recheck soon.",
        "High": "Perform urgent on-site inspection and safety assessment.",
    }
    return recommendations[risk_level]


def _fallback_causes(crack_detected: bool, risk_level: str) -> list[str]:
    if not crack_detected:
        return [
            "No clear surface crack pattern is visible in the submitted image.",
            "Observed texture variation may be caused by lighting, stains, or surface wear.",
            "Routine environmental exposure remains the main background factor to monitor.",
        ]
    if risk_level == "High":
        return [
            "Localized tensile stress or repeated load concentration may have opened the crack.",
            "Water ingress and thermal cycling may have accelerated crack propagation.",
            "Material aging or construction defects may have weakened the surface layer.",
        ]
    return [
        "Early-stage tensile stress may be affecting the visible surface region.",
        "Moisture movement or thermal expansion may be contributing to crack initiation.",
        "Localized material fatigue may be causing minor crack development.",
    ]


def _fallback_risks(crack_detected: bool, risk_level: str) -> list[str]:
    if not crack_detected:
        return [
            "No immediate structural risk is visible from this image alone.",
            "Hidden defects still cannot be fully ruled out without periodic inspection.",
            "Future deterioration may occur if environmental exposure intensifies.",
        ]
    if risk_level == "High":
        return [
            "Crack propagation may expand under repeated loading or vibration.",
            "Moisture penetration may trigger corrosion or internal weakening.",
            "Serviceability and local safety conditions may degrade without prompt inspection.",
        ]
    return [
        "The crack may widen if surface stress continues to accumulate.",
        "Water penetration may gradually reduce durability around the affected area.",
        "If not monitored, the defect may develop into a more critical maintenance issue.",
    ]


def _fallback_treatment_options(crack_detected: bool, risk_level: str) -> list[str]:
    if not crack_detected:
        return [
            "Continue routine visual monitoring and keep a dated inspection record.",
            "Re-capture images under stable lighting for comparison during the next inspection cycle.",
            "Escalate to manual inspection only if new visible defects appear.",
        ]
    if risk_level == "High":
        return [
            "Arrange urgent on-site engineering inspection and document crack dimensions.",
            "Apply temporary safety control measures and restrict exposure if the area is critical.",
            "Plan targeted repair such as sealing, grouting, or structural reinforcement after inspection.",
        ]
    return [
        "Schedule a manual inspection to confirm crack depth, width, and development trend.",
        "Use short-cycle monitoring with repeated imaging to track visible changes over time.",
        "Prepare localized maintenance such as sealing or surface repair if the defect remains stable.",
    ]


def _normalize_list(raw_value: Any, fallback_items: list[str]) -> list[str]:
    if isinstance(raw_value, list):
        cleaned = [str(item).strip() for item in raw_value if str(item).strip()]
    else:
        cleaned = []
    while len(cleaned) < 3:
        cleaned.append(fallback_items[len(cleaned)])
    return cleaned[:3]


def _build_intelligence_report(
    crack_detected: bool,
    risk_level: str,
    causes: list[str],
    risks: list[str],
    treatment_options: list[str],
    raw_report: Any,
) -> str:
    report = str(raw_report or "").strip()
    if report:
        return report

    status = (
        "No clear crack signature is visible in the current image."
        if not crack_detected
        else f"A potential crack indication is present and is currently classified as {risk_level} risk."
    )
    return (
        f"{status} The most likely contributing factors are {causes[0].lower()} and "
        f"{causes[1].lower()}. The main operational concerns are {risks[0].lower()} and "
        f"{risks[1].lower()}. Recommended response options include {treatment_options[0].lower()}, "
        f"{treatment_options[1].lower()}, and {treatment_options[2].lower()}"
    )


def _normalize_location_hint(raw_hint: Any) -> dict[str, Any]:
    if not isinstance(raw_hint, dict):
        return {"mode": "none", "description": "No precise localization available."}

    mode = str(raw_hint.get("mode", "none")).strip().lower()
    if mode not in {"bbox", "region", "none"}:
        mode = "region" if raw_hint.get("description") else "none"

    normalized = {
        "mode": mode,
        "x": max(0, min(100, int(raw_hint.get("x", 15) or 15))),
        "y": max(0, min(100, int(raw_hint.get("y", 15) or 15))),
        "width": max(1, min(100, int(raw_hint.get("width", 35) or 35))),
        "height": max(1, min(100, int(raw_hint.get("height", 20) or 20))),
        "description": str(raw_hint.get("description", "") or "").strip(),
    }
    if mode == "none" and not normalized["description"]:
        normalized["description"] = "No precise localization available."
    return normalized


def _normalize_result(raw_result: dict[str, Any], model_name: str) -> dict[str, Any]:
    crack_detected = _normalize_bool(raw_result.get("crack_detected", False))
    risk_level = _normalize_risk_level(raw_result.get("risk_level"), crack_detected)
    judgement = "Crack Detected" if crack_detected else "No Crack Detected"
    explanation = str(raw_result.get("explanation", "") or "").strip()
    if not explanation:
        explanation = (
            "The model identified visible crack-like features."
            if crack_detected
            else "No clear crack-like features were detected in the image."
        )
    causes = _normalize_list(
        raw_result.get("possible_causes"),
        _fallback_causes(crack_detected, risk_level),
    )
    risks = _normalize_list(
        raw_result.get("potential_risks"),
        _fallback_risks(crack_detected, risk_level),
    )
    treatment_options = _normalize_list(
        raw_result.get("treatment_options"),
        _fallback_treatment_options(crack_detected, risk_level),
    )
    intelligence_report = _build_intelligence_report(
        crack_detected=crack_detected,
        risk_level=risk_level,
        causes=causes,
        risks=risks,
        treatment_options=treatment_options,
        raw_report=raw_result.get("intelligence_report"),
    )

    return {
        "crack_detected": crack_detected,
        "judgement": judgement,
        "risk_level": risk_level,
        "recommendation": _normalize_recommendation(risk_level),
        "explanation": explanation,
        "intelligence_report": intelligence_report,
        "possible_causes": causes,
        "potential_risks": risks,
        "treatment_options": treatment_options,
        "location_hint": _normalize_location_hint(raw_result.get("location_hint")),
        "model_used": model_name,
    }


def _save_upload(file: FileStorage, basename: str) -> tuple[Path, str]:
    suffix = file.filename.rsplit(".", 1)[1].lower()
    original_path = Config.TEMP_DIR / f"{basename}_original.{suffix}"
    file.save(original_path)
    try:
        with Image.open(original_path) as image:
            image.verify()
    except (UnidentifiedImageError, OSError) as exc:
        original_path.unlink(missing_ok=True)
        raise AnalysisError("The uploaded file is not a valid image.") from exc
    mime_type = "image/png" if suffix == "png" else "image/jpeg"
    return original_path, mime_type


def analyze_upload(file: FileStorage) -> dict[str, Any]:
    cleanup_temp_files()

    if not file or not file.filename:
        raise AnalysisError("Please upload an image file.")
    if not allowed_file(file.filename):
        raise AnalysisError("Only JPG, JPEG, and PNG files are supported.")
    if file.mimetype not in ALLOWED_MIME_TYPES:
        raise AnalysisError("Unsupported MIME type. Please upload a valid image.")

    basename = uuid.uuid4().hex
    safe_name = secure_filename(file.filename)
    if "." not in safe_name:
        raise AnalysisError("The uploaded file is missing a valid extension.")

    original_path, mime_type = _save_upload(file, basename)
    image_bytes = original_path.read_bytes()

    errors: list[str] = []
    final_result: dict[str, Any] | None = None
    for _, adapter, model_name in PROVIDERS:
        try:
            raw = adapter(
                image_bytes=image_bytes,
                mime_type=mime_type,
                api_key=Config.API_KEY,
                api_base_url=Config.API_BASE_URL,
                model_name=model_name,
                timeout=Config.REQUEST_TIMEOUT,
            )
            final_result = _normalize_result(raw, model_name)
            break
        except Exception as exc:
            errors.append(f"{model_name}: {exc}")

    if final_result is None:
        original_path.unlink(missing_ok=True)
        raise AnalysisError(
            "All configured models failed to analyze the image. "
            f"Details: {' | '.join(errors[:3])}"
        )

    annotated_path = Config.TEMP_DIR / f"{basename}_annotated.png"
    create_annotation(
        original_path=original_path,
        output_path=annotated_path,
        location_hint=final_result["location_hint"],
        explanation=final_result["explanation"],
    )
    final_result["original_image_url"] = f"/temp/{original_path.name}"
    final_result["annotated_image_url"] = f"/temp/{annotated_path.name}"
    return final_result
