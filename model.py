"""
model.py — CyberFury AI Forensic Lab
Handles model loading, image validation, prediction, and explainability.
"""

import torch
import streamlit as st
from transformers import AutoImageProcessor, AutoModelForImageClassification
from PIL import Image
import numpy as np

# ─── Model Registry ───────────────────────────────────────────────────────────
# Primary model — lightweight SDXL-tuned binary classifier
PRIMARY_MODEL_ID = "Organika/sdxl-detector"

# Secondary model for ensemble detection (if unavailable, falls back to primary)
SECONDARY_MODEL_ID = "umm-maybe/AI-image-detector"

# ─── Ensemble Configuration ────────────────────────────────────────────────────
# Weights for weighted averaging of ensemble predictions
PRIMARY_MODEL_WEIGHT = 0.6
SECONDARY_MODEL_WEIGHT = 0.4

# ─── Constraints ──────────────────────────────────────────────────────────────
MAX_PIXELS     = 4096       # max dimension (px)
MIN_PIXELS     = 32         # min dimension (px)
MAX_FILE_MB    = 15         # hard limit for file size

# Keywords used to locate the "AI / fake" label in id2label dict
_AI_KEYWORDS   = {"artificial", "fake", "ai", "sdxl", "generated", "synthetic"}
_REAL_KEYWORDS = {"real", "authentic", "natural", "human", "genuine", "photo"}


# ─── Validation ───────────────────────────────────────────────────────────────

def validate_image(image: Image.Image) -> tuple[bool, str]:
    """
    Validate that the image is processable.
    Returns (ok: bool, message: str).
    """
    if image.mode not in ("RGB", "RGBA", "L", "P", "CMYK", "YCbCr"):
        return False, f"Unsupported colour mode: {image.mode}"

    w, h = image.size
    if w > MAX_PIXELS or h > MAX_PIXELS:
        return False, (
            f"Image dimensions too large ({w}×{h}). "
            f"Maximum supported: {MAX_PIXELS}×{MAX_PIXELS} px."
        )
    if w < MIN_PIXELS or h < MIN_PIXELS:
        return False, (
            f"Image too small ({w}×{h}). "
            f"Minimum supported: {MIN_PIXELS}×{MIN_PIXELS} px."
        )
    return True, "OK"


# ─── Model Loading ────────────────────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def load_primary_model():
    """
    Load and cache the primary detection model.
    Called once per Streamlit session; subsequent calls return from cache.
    """
    try:
        processor = AutoImageProcessor.from_pretrained(PRIMARY_MODEL_ID, use_fast=True)
        model     = AutoModelForImageClassification.from_pretrained(PRIMARY_MODEL_ID)
        device    = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model.to(device).eval()
        return processor, model, device
    except Exception as exc:
        raise RuntimeError(f"Model load failed: {exc}") from exc


@st.cache_resource(show_spinner=False)
def load_secondary_model():
    """
    Load and cache the secondary detection model for ensemble inference.
    Returns None if secondary model load fails (graceful degradation).
    """
    try:
        processor = AutoImageProcessor.from_pretrained(SECONDARY_MODEL_ID, use_fast=True)
        model     = AutoModelForImageClassification.from_pretrained(SECONDARY_MODEL_ID)
        device    = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model.to(device).eval()
        return processor, model, device
    except Exception:
        # Graceful fallback: return None if secondary model unavailable
        return None


# ─── Prediction ───────────────────────────────────────────────────────────────

def _resolve_ai_label(id2label: dict) -> tuple[int | None, int | None]:
    """
    Scan id2label to find which index corresponds to AI-generated content
    and which to authentic content.  Returns (ai_idx, real_idx).
    Falls back to (0, 1) if detection is ambiguous.
    """
    ai_idx   = None
    real_idx = None

    for idx, label in id2label.items():
        lwr = label.lower()
        if any(k in lwr for k in _AI_KEYWORDS):
            ai_idx = idx
        elif any(k in lwr for k in _REAL_KEYWORDS):
            real_idx = idx

    # Fallback: assume index 0 = AI, 1 = real (common convention)
    if ai_idx is None:
        ai_idx = 0
    if real_idx is None:
        real_idx = 1 if len(id2label) > 1 else 0

    return ai_idx, real_idx


def _run_inference(image: Image.Image, processor, model, device) -> dict:
    """
    Core inference routine.
    Returns a dict with all raw probability information.
    """
    # Ensure RGB — necessary for most vision transformers
    if image.mode != "RGB":
        image = image.convert("RGB")

    inputs = processor(images=image, return_tensors="pt").to(device)

    with torch.no_grad():
        logits = model(**inputs).logits
        probs  = torch.nn.functional.softmax(logits, dim=-1)[0].cpu().tolist()

    id2label   = model.config.id2label                       # e.g. {0: "artificial", 1: "real"}
    ai_idx, real_idx = _resolve_ai_label(id2label)

    # Build a clean scores dict keyed by human-readable label
    scores = {id2label[i]: round(probs[i] * 100, 3) for i in range(len(probs))}

    ai_score   = probs[ai_idx]   * 100
    real_score = probs[real_idx] * 100

    predicted_idx   = int(np.argmax(probs))
    predicted_label = id2label[predicted_idx]

    return {
        "predicted_label": predicted_label,
        "ai_score":        round(ai_score,   2),   # % probability of being AI-generated
        "real_score":      round(real_score, 2),   # % probability of being authentic
        "confidence":      round(probs[predicted_idx] * 100, 2),
        "all_scores":      scores,
        "is_fake":         ai_score > 50.0,
        "id2label":        id2label,
    }


def _run_ensemble_inference(image: Image.Image) -> dict:
    """
    Run ensemble inference using both primary and secondary models.
    Performs weighted averaging and agreement detection.
    Returns a structured result dict with individual model outputs and ensemble verdict.
    """
    # Load models (cached)
    primary_processor, primary_model, primary_device = load_primary_model()
    
    secondary_data = load_secondary_model()
    has_secondary = secondary_data is not None
    
    # Run primary inference
    primary_result = _run_inference(image, primary_processor, primary_model, primary_device)
    
    models_data = [
        {
            "name": "Primary (Organika/sdxl-detector)",
            "ai_score": primary_result["ai_score"],
            "real_score": primary_result["real_score"],
            "label": primary_result["predicted_label"],
        }
    ]
    
    # Run secondary inference if available
    if has_secondary:
        secondary_processor, secondary_model, secondary_device = secondary_data
        secondary_result = _run_inference(image, secondary_processor, secondary_model, secondary_device)
        
        models_data.append({
            "name": "Secondary (umm-maybe/AI-image-detector)",
            "ai_score": secondary_result["ai_score"],
            "real_score": secondary_result["real_score"],
            "label": secondary_result["predicted_label"],
        })
        
        # Weighted average of AI scores
        ensemble_ai_score = (
            (primary_result["ai_score"] * PRIMARY_MODEL_WEIGHT) +
            (secondary_result["ai_score"] * SECONDARY_MODEL_WEIGHT)
        )
        
        # Agreement detection: check if both models agree on verdict
        primary_is_fake = primary_result["is_fake"]
        secondary_is_fake = secondary_result["is_fake"]
        models_agree = primary_is_fake == secondary_is_fake
    else:
        # Fallback: only primary model available
        ensemble_ai_score = primary_result["ai_score"]
        models_agree = True  # Trivially true with one model
    
    # Determine final verdict based on weighted ensemble score
    ensemble_is_fake = ensemble_ai_score > 50.0
    ensemble_verdict = "DEEPFAKE" if ensemble_is_fake else "AUTHENTIC"
    
    return {
        "final_verdict": ensemble_verdict,
        "final_ai_score": round(ensemble_ai_score, 2),
        "ensemble_real_score": round(100 - ensemble_ai_score, 2),
        "confidence": round(abs(ensemble_ai_score - 50.0) + 50.0, 2),  # Higher when far from 50%
        "agreement": models_agree,
        "has_secondary": has_secondary,
        "models": models_data,
        # Legacy fields for backward compatibility
        "predicted_label": "ensemble",
        "ai_score": round(ensemble_ai_score, 2),
        "real_score": round(100 - ensemble_ai_score, 2),
        "is_fake": ensemble_is_fake,
        "all_scores": {"AI": round(ensemble_ai_score, 2), "Real": round(100 - ensemble_ai_score, 2)},
    }


def get_confidence_tier(score: float) -> tuple[str, str]:
    """
    Map a [0,100] AI score to a human tier and theme colour.
    Returns (tier_label, hex_colour).
    """
    if score >= 90:
        return "High Confidence",   "#EB5757"
    elif score >= 60:
        return "Medium Confidence", "#F2994A"
    else:
        return "Uncertain",         "#F2C94C"


# ─── Explainability ───────────────────────────────────────────────────────────

def _build_explanation(result: dict) -> list[dict]:
    """
    Generate a list of explanation items (icon, heading, body) for the UI.
    These are heuristic, model-agnostic interpretations.
    """
    score  = result["ai_score"]
    is_fake = result["is_fake"]
    tier, _ = get_confidence_tier(score)
    items  = []

    if is_fake:
        items.append({
            "icon": "🔬",
            "heading": "Synthetic Pixel Distribution",
            "body": (
                f"The model assigned {score:.1f}% probability to AI generation. "
                "GAN- and diffusion-based images leave characteristic frequency-domain "
                "artefacts that differ from real camera noise."
            ),
        })
        if score > 90:
            items.append({
                "icon": "⚡",
                "heading": "High-Confidence Synthetic Indicators",
                "body": (
                    "Upsampling grids, unnaturally smooth textures, and spectral "
                    "fingerprints consistent with diffusion-model pipelines were detected."
                ),
            })
            items.append({
                "icon": "📐",
                "heading": "Structural Regularity",
                "body": (
                    "AI images often exhibit perfect symmetry and unrealistic lighting "
                    "gradients. Real photographs show stochastic imperfections."
                ),
            })
        elif score > 60:
            items.append({
                "icon": "🌀",
                "heading": "Partial Synthetic Patterns",
                "body": (
                    "Some AI fingerprints were found, but heavy compression, cropping, "
                    "or post-processing may have partially masked synthetic origin."
                ),
            })
        else:
            items.append({
                "icon": "❓",
                "heading": "Inconclusive Signal",
                "body": (
                    "The model is not confident enough to make a reliable call. "
                    "Consider corroborating with metadata analysis and reverse image search."
                ),
            })
    else:
        real = result["real_score"]
        items.append({
            "icon": "📷",
            "heading": "Natural Camera Noise Profile",
            "body": (
                f"The model assigned {real:.1f}% probability to authentic capture. "
                "Camera sensor noise and natural optical aberrations match expected patterns."
            ),
        })
        if real > 90:
            items.append({
                "icon": "✅",
                "heading": "Authentic Pixel Statistics",
                "body": (
                    "Colour histograms, high-frequency noise, and demosaicing artefacts "
                    "are consistent with real camera output rather than AI synthesis."
                ),
            })
        elif real > 60:
            items.append({
                "icon": "⚠️",
                "heading": "Minor Editing Detected",
                "body": (
                    "The image appears real but shows signs of post-processing. "
                    "Heavy retouching can partially mimic AI-generation signatures."
                ),
            })
        else:
            items.append({
                "icon": "❓",
                "heading": "Low-Confidence Authentic Call",
                "body": (
                    "Authenticity signals are weak. Independent verification is strongly "
                    "recommended before acting on this result."
                ),
            })

    return items


# ─── Public API ───────────────────────────────────────────────────────────────

def analyze_image(image: Image.Image) -> dict:
    """
    Full pipeline: validate → load models → ensemble infer → interpret.
    Always returns a dict; on failure the dict contains an 'error' key.
    """
    try:
        # 1. Validate
        ok, msg = validate_image(image)
        if not ok:
            return {"error": msg}

        # 2. Run ensemble inference (loads both models, cached after first call)
        ensemble_result = _run_ensemble_inference(image)

        # 3. Enrich with UI metadata
        tier, colour             = get_confidence_tier(ensemble_result["ai_score"])
        ensemble_result["conf_label"]     = tier
        ensemble_result["conf_colour"]    = colour
        ensemble_result["verdict"]        = ensemble_result["final_verdict"]
        ensemble_result["verdict_colour"] = "#EB5757" if ensemble_result["is_fake"] else "#27AE60"
        ensemble_result["explanation"]    = _build_explanation(ensemble_result)

        return ensemble_result

    except RuntimeError as exc:
        return {"error": str(exc)}
    except Exception as exc:
        return {"error": f"Unexpected error during analysis: {exc}"}
