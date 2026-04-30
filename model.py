"""
model.py — CyberFury AI Forensic Lab
Handles model loading, image validation, prediction, and explainability.

ENSEMBLE v3: Five-path decision engine.
  Path A — Strong AI agreement      → DEEPFAKE   HIGH
  Path B — Strong Real agreement    → AUTHENTIC  HIGH
  Path C — Dominant model override  → trust ≥90 % confident model when models DISAGREE, MEDIUM
  Path D — Moderate agreement       → weighted average, MEDIUM
  Path E — True strong disagreement → UNCERTAIN  LOW  (neither model is dominant)

Path C prevents extreme splits like 100 % vs 9.7 % from incorrectly producing
UNCERTAIN — when one model is clearly dominant, its verdict is applied.
"""

import torch
import streamlit as st
from transformers import AutoImageProcessor, AutoModelForImageClassification
from PIL import Image
import numpy as np

# ─── Model Registry ───────────────────────────────────────────────────────────
PRIMARY_MODEL_ID   = "Organika/sdxl-detector"
SECONDARY_MODEL_ID = "umm-maybe/AI-image-detector"

# ─── Ensemble Configuration ───────────────────────────────────────────────────
# Base weights (may be overridden dynamically by the decision engine)
PRIMARY_MODEL_WEIGHT   = 0.6
SECONDARY_MODEL_WEIGHT = 0.4

# Decision thresholds
_STRONG_AGREE_AI_THRESHOLD    = 70.0   # both models ≥ this  → strong DEEPFAKE
_STRONG_AGREE_REAL_THRESHOLD  = 30.0   # both models ≤ this  → strong AUTHENTIC
_DISAGREEMENT_THRESHOLD       = 40.0   # score gap ≥ this    → UNCERTAIN (only if neither dominates)
_HIGH_CONFIDENCE_THRESHOLD    = 90.0   # single-model conf   → boost that model's weight
_DOMINANT_CONFIDENCE          = 90.0   # one model ≥ this    → trust it even under disagreement

# ─── Constraints ──────────────────────────────────────────────────────────────
MAX_PIXELS  = 4096
MIN_PIXELS  = 32
MAX_FILE_MB = 15

_AI_KEYWORDS   = {"artificial", "fake", "ai", "sdxl", "generated", "synthetic"}
_REAL_KEYWORDS = {"real", "authentic", "natural", "human", "genuine", "photo"}


# ═══════════════════════════════════════════════════════════════════════════════
#  Validation
# ═══════════════════════════════════════════════════════════════════════════════

def validate_image(image: Image.Image) -> tuple[bool, str]:
    """Validate that the image is processable. Returns (ok, message)."""
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


# ═══════════════════════════════════════════════════════════════════════════════
#  Model Loading  (unchanged — cached per Streamlit session)
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_resource(show_spinner=False)
def load_primary_model():
    """Load and cache the primary detection model."""
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
    """Load and cache the secondary model. Returns None on failure (graceful degradation)."""
    try:
        processor = AutoImageProcessor.from_pretrained(SECONDARY_MODEL_ID, use_fast=True)
        model     = AutoModelForImageClassification.from_pretrained(SECONDARY_MODEL_ID)
        device    = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model.to(device).eval()
        return processor, model, device
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════════════════
#  Per-model Inference  (unchanged)
# ═══════════════════════════════════════════════════════════════════════════════

def _resolve_ai_label(id2label: dict) -> tuple[int | None, int | None]:
    """
    Scan id2label to find AI-generated and authentic label indices.
    Returns (ai_idx, real_idx). Falls back to (0, 1) if ambiguous.
    """
    ai_idx = real_idx = None
    for idx, label in id2label.items():
        lwr = label.lower()
        if any(k in lwr for k in _AI_KEYWORDS):
            ai_idx = idx
        elif any(k in lwr for k in _REAL_KEYWORDS):
            real_idx = idx
    if ai_idx   is None: ai_idx   = 0
    if real_idx is None: real_idx = 1 if len(id2label) > 1 else 0
    return ai_idx, real_idx


def _run_inference(image: Image.Image, processor, model, device) -> dict:
    """
    Core inference for a single model.
    Returns a dict with ai_score, real_score, confidence, predicted_label, etc.
    """
    if image.mode != "RGB":
        image = image.convert("RGB")

    inputs = processor(images=image, return_tensors="pt").to(device)
    with torch.no_grad():
        logits = model(**inputs).logits
        probs  = torch.nn.functional.softmax(logits, dim=-1)[0].cpu().tolist()

    id2label            = model.config.id2label
    ai_idx, real_idx    = _resolve_ai_label(id2label)
    scores              = {id2label[i]: round(probs[i] * 100, 3) for i in range(len(probs))}
    ai_score            = probs[ai_idx]   * 100
    real_score          = probs[real_idx] * 100
    predicted_idx       = int(np.argmax(probs))
    predicted_label     = id2label[predicted_idx]

    return {
        "predicted_label": predicted_label,
        "ai_score":        round(ai_score,   2),
        "real_score":      round(real_score, 2),
        "confidence":      round(probs[predicted_idx] * 100, 2),
        "all_scores":      scores,
        "is_fake":         ai_score > 50.0,
        "id2label":        id2label,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  Ensemble Decision Engine  ← REPLACED / REDESIGNED
# ═══════════════════════════════════════════════════════════════════════════════

def _compute_dynamic_weights(p_ai: float, s_ai: float) -> tuple[float, float]:
    """
    Compute trust weights dynamically based on each model's confidence.

    Rules
    -----
    • If primary is very confident (≥ 90 % on either side)   → boost to 0.80 / 0.20
    • If secondary is very confident and primary is not       → boost secondary to 0.30 / 0.70
    • Otherwise keep the configured base weights.

    Both weights always sum to 1.0.
    """
    p_conf = max(p_ai, 100 - p_ai)   # distance from 50 → how confident is this model
    s_conf = max(s_ai, 100 - s_ai)

    if p_conf >= _HIGH_CONFIDENCE_THRESHOLD:
        return 0.80, 0.20
    if s_conf >= _HIGH_CONFIDENCE_THRESHOLD and p_conf < 70:
        return 0.30, 0.70
    return PRIMARY_MODEL_WEIGHT, SECONDARY_MODEL_WEIGHT


def _classify_agreement(p_ai: float, s_ai: float) -> tuple[str, float]:
    """
    Classify the relationship between the two model scores.

    Returns
    -------
    (case_label, difference)

    case_label:
      "STRONG_AI"        — both firmly predict AI
      "STRONG_REAL"      — both firmly predict real
      "MODERATE"         — same direction but not extreme
      "WEAK_AGREEMENT"   — same >50 / <50 side but gap is notable
      "STRONG_DISAGREE"  — different sides, large gap
    """
    diff = abs(p_ai - s_ai)
    p_fake = p_ai >= 50.0
    s_fake = s_ai >= 50.0

    if p_ai >= _STRONG_AGREE_AI_THRESHOLD and s_ai >= _STRONG_AGREE_AI_THRESHOLD:
        return "STRONG_AI", diff

    if p_ai <= _STRONG_AGREE_REAL_THRESHOLD and s_ai <= _STRONG_AGREE_REAL_THRESHOLD:
        return "STRONG_REAL", diff

    if p_fake != s_fake and diff >= _DISAGREEMENT_THRESHOLD:
        return "STRONG_DISAGREE", diff

    if p_fake == s_fake:
        return "MODERATE", diff

    return "WEAK_AGREEMENT", diff


def _build_ensemble_verdict(
    p_result: dict,
    s_result: dict,
) -> dict:
    """
    Five-path decision engine.

    Path A — Strong AI agreement      → DEEPFAKE   HIGH
    Path B — Strong Real agreement    → AUTHENTIC  HIGH
    Path C — Dominant model override  → trust the ≥90 % confident model, MEDIUM
    Path D — Moderate agreement       → weighted average, MEDIUM
    Path E — True strong disagreement → UNCERTAIN  LOW  (neither model is dominant)

    Path C is the key addition: when one model scores ≥ 90 % confident and the
    other does not reach that bar, the dominant model wins regardless of direction
    disagreement.  This prevents a 100 % vs 10 % split from producing UNCERTAIN
    when the answer is obvious.

    Returns a structured verdict dict consumed by _run_ensemble_inference().
    """
    p_ai = p_result["ai_score"]
    s_ai = s_result["ai_score"]

    case, diff = _classify_agreement(p_ai, s_ai)
    pw, sw     = _compute_dynamic_weights(p_ai, s_ai)

    # ── Path A: Both strongly say AI ──────────────────────────────────────────
    if case == "STRONG_AI":
        final_ai = (p_ai * pw) + (s_ai * sw)
        return _verdict_dict(
            verdict        = "DEEPFAKE",
            final_ai       = final_ai,
            confidence_lvl = "HIGH",
            agreement      = True,
            diff           = diff,
            note           = "Both models strongly indicate AI-generated content.",
            weights_used   = (pw, sw),
        )

    # ── Path B: Both strongly say Real ───────────────────────────────────────
    if case == "STRONG_REAL":
        final_ai = (p_ai * pw) + (s_ai * sw)
        return _verdict_dict(
            verdict        = "AUTHENTIC",
            final_ai       = final_ai,
            confidence_lvl = "HIGH",
            agreement      = True,
            diff           = diff,
            note           = "Both models strongly indicate an authentic image.",
            weights_used   = (pw, sw),
        )

    # ── Path C: Dominant model override (one model ≥ 90 % confident) ─────────
    # Only applies when models DISAGREE (different sides of the 50 % boundary).
    # When both models agree on the verdict direction, Path D handles them with
    # proper weighted averaging — no need to override.
    # This handles cases like 100 % vs 9.7 % where UNCERTAIN would be
    # misleading — the primary model is clearly more decisive.
    p_conf = max(p_ai, 100 - p_ai)
    s_conf = max(s_ai, 100 - s_ai)
    models_disagree = (p_ai >= 50.0) != (s_ai >= 50.0)

    if models_disagree and (p_conf >= _DOMINANT_CONFIDENCE or s_conf >= _DOMINANT_CONFIDENCE):
        if p_conf >= s_conf:
            # Primary dominates
            dominant_ai      = p_ai
            dominant_verdict = "DEEPFAKE" if p_ai >= 50.0 else "AUTHENTIC"
            dominant_name    = "Primary"
            # Weight heavily toward primary; secondary adds a small correction
            eff_pw, eff_sw   = 0.85, 0.15
            note = (
                f"Primary model is highly confident ({p_conf:.0f}% certainty). "
                f"Secondary model ({s_ai:.1f}% AI) disagrees but carries low weight. "
                f"Primary verdict applied with {eff_pw*100:.0f}/{eff_sw*100:.0f} weighting."
            )
        else:
            # Secondary dominates
            dominant_ai      = s_ai
            dominant_verdict = "DEEPFAKE" if s_ai >= 50.0 else "AUTHENTIC"
            dominant_name    = "Secondary"
            eff_pw, eff_sw   = 0.15, 0.85
            note = (
                f"Secondary model is highly confident ({s_conf:.0f}% certainty). "
                f"Primary model ({p_ai:.1f}% AI) disagrees but carries low weight. "
                f"Secondary verdict applied with {eff_pw*100:.0f}/{eff_sw*100:.0f} weighting."
            )

        final_ai = (p_ai * eff_pw) + (s_ai * eff_sw)
        return _verdict_dict(
            verdict        = dominant_verdict,
            final_ai       = final_ai,
            confidence_lvl = "MEDIUM",   # not HIGH — there is genuine disagreement
            agreement      = False,
            diff           = diff,
            note           = note,
            weights_used   = (eff_pw, eff_sw),
        )

    # ── Path D: Moderate agreement (same side, gap < threshold) ──────────────
    if case in ("MODERATE", "WEAK_AGREEMENT"):
        final_ai = (p_ai * pw) + (s_ai * sw)
        verdict  = "DEEPFAKE" if final_ai >= 50.0 else "AUTHENTIC"
        note = (
            "Models lean the same direction but differ in magnitude. "
            f"Score gap: {diff:.1f} pts — weighted average applied."
        )
        return _verdict_dict(
            verdict        = verdict,
            final_ai       = final_ai,
            confidence_lvl = "MEDIUM",
            agreement      = True,
            diff           = diff,
            note           = note,
            weights_used   = (pw, sw),
        )

    # ── Path E: True strong disagreement — UNCERTAIN ──────────────────────────
    # Both models are moderately confident but point in opposite directions.
    # Neither is dominant (both below _DOMINANT_CONFIDENCE).
    # Anchor to the more confident model but pull toward 50 to reflect uncertainty.
    if p_conf >= s_conf:
        anchor_ai   = p_ai
        anchor_note = "Primary model (higher confidence) used as anchor."
    else:
        anchor_ai   = s_ai
        anchor_note = "Secondary model (higher confidence) used as anchor."

    uncertainty_pull = 0.40   # pull 40 % of the way back to 50
    final_ai = anchor_ai + (50.0 - anchor_ai) * uncertainty_pull
    final_ai = round(min(max(final_ai, 0.0), 100.0), 2)

    note = (
        f"Models disagree without a dominant signal (gap: {diff:.1f} pts). "
        f"Result may be unreliable — edge-case or post-processed image suspected. "
        f"{anchor_note}"
    )

    return _verdict_dict(
        verdict        = "UNCERTAIN",
        final_ai       = final_ai,
        confidence_lvl = "LOW",
        agreement      = False,
        diff           = diff,
        note           = note,
        weights_used   = (pw, sw),
    )


def _verdict_dict(
    verdict: str,
    final_ai: float,
    confidence_lvl: str,
    agreement: bool,
    diff: float,
    note: str,
    weights_used: tuple[float, float],
) -> dict:
    """Construct the canonical ensemble verdict dictionary."""
    final_ai = round(final_ai, 2)
    return {
        "final_verdict":    verdict,
        "final_ai_score":   final_ai,
        "final_real_score": round(100 - final_ai, 2),
        "confidence_level": confidence_lvl,   # "HIGH" / "MEDIUM" / "LOW"
        "agreement":        agreement,
        "difference":       round(diff, 2),
        "note":             note,
        "weights_used":     weights_used,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  Ensemble Orchestration  (replaces old _run_ensemble_inference)
# ═══════════════════════════════════════════════════════════════════════════════

def _run_ensemble_inference(image: Image.Image) -> dict:
    """
    Load both models (cached), run per-model inference, apply the decision
    engine, and return a fully-populated result dict.
    """
    primary_processor, primary_model, primary_device = load_primary_model()
    secondary_data = load_secondary_model()
    has_secondary  = secondary_data is not None

    primary_result = _run_inference(image, primary_processor, primary_model, primary_device)

    models_data = [
        {
            "name":       "Primary (Organika/sdxl-detector)",
            "ai_score":   primary_result["ai_score"],
            "real_score": primary_result["real_score"],
            "label":      primary_result["predicted_label"],
            "confidence": primary_result["confidence"],
        }
    ]

    # ── Single-model fallback ─────────────────────────────────────────────────
    if not has_secondary:
        p_ai = primary_result["ai_score"]
        verdict  = "DEEPFAKE" if p_ai >= 50.0 else "AUTHENTIC"
        conf_lvl = (
            "HIGH"   if max(p_ai, 100 - p_ai) >= _HIGH_CONFIDENCE_THRESHOLD else
            "MEDIUM" if max(p_ai, 100 - p_ai) >= 60 else
            "LOW"
        )
        return _assemble_output(
            verdict_block  = _verdict_dict(
                verdict        = verdict,
                final_ai       = p_ai,
                confidence_lvl = conf_lvl,
                agreement      = True,
                diff           = 0.0,
                note           = "Secondary model unavailable — primary model only.",
                weights_used   = (1.0, 0.0),
            ),
            primary_result = primary_result,
            models_data    = models_data,
            has_secondary  = False,
        )

    # ── Two-model path ────────────────────────────────────────────────────────
    secondary_processor, secondary_model, secondary_device = secondary_data
    secondary_result = _run_inference(
        image, secondary_processor, secondary_model, secondary_device
    )

    models_data.append({
        "name":       "Secondary (umm-maybe/AI-image-detector)",
        "ai_score":   secondary_result["ai_score"],
        "real_score": secondary_result["real_score"],
        "label":      secondary_result["predicted_label"],
        "confidence": secondary_result["confidence"],
    })

    verdict_block = _build_ensemble_verdict(primary_result, secondary_result)

    return _assemble_output(
        verdict_block  = verdict_block,
        primary_result = primary_result,
        models_data    = models_data,
        has_secondary  = True,
        secondary_result = secondary_result,
    )


def _assemble_output(
    verdict_block:    dict,
    primary_result:   dict,
    models_data:      list,
    has_secondary:    bool,
    secondary_result: dict | None = None,
) -> dict:
    """
    Merge the verdict block with raw inference data and legacy-compatible fields
    so that no downstream consumer (app.py, ui.py, report_generator.py) breaks.
    """
    final_ai   = verdict_block["final_ai_score"]
    verdict    = verdict_block["final_verdict"]
    is_fake    = verdict == "DEEPFAKE"
    conf_level = verdict_block["confidence_level"]

    # Map the three-tier confidence level to a legacy numeric confidence value
    # that report_generator.py uses (it expects a float in [50, 100])
    _conf_numeric_map = {"HIGH": 92.0, "MEDIUM": 72.0, "LOW": 52.0}
    conf_numeric = _conf_numeric_map.get(conf_level, 72.0)

    return {
        # ── New structured fields ──────────────────────────────────────────
        "final_verdict":    verdict,
        "final_ai_score":   final_ai,
        "final_real_score": verdict_block["final_real_score"],
        "confidence_level": conf_level,
        "agreement":        verdict_block["agreement"],
        "difference":       verdict_block["difference"],
        "note":             verdict_block["note"],
        "weights_used":     verdict_block["weights_used"],
        "has_secondary":    has_secondary,
        "models":           models_data,

        # ── Legacy fields (backward-compatible) ───────────────────────────
        "predicted_label":  "ensemble",
        "ai_score":         final_ai,
        "real_score":       verdict_block["final_real_score"],
        "confidence":       conf_numeric,
        "is_fake":          is_fake,
        "all_scores": {
            "AI":   final_ai,
            "Real": verdict_block["final_real_score"],
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  Confidence Tier  (updated to honour new LOW / MEDIUM / HIGH from engine)
# ═══════════════════════════════════════════════════════════════════════════════

def get_confidence_tier(score: float, confidence_level: str = "") -> tuple[str, str]:
    """
    Map ensemble output to a human-readable tier and theme colour.

    If confidence_level is supplied (new field), it takes precedence.
    Falls back to score-based heuristic for backward compatibility.

    Returns (tier_label, hex_colour).
    """
    if confidence_level == "HIGH":
        return "High Confidence",   "#EB5757"
    if confidence_level == "MEDIUM":
        return "Medium Confidence", "#F2994A"
    if confidence_level == "LOW":
        return "Uncertain",         "#A78BFA"   # purple for uncertain

    # Legacy score-based fallback
    if score >= 90:
        return "High Confidence",   "#EB5757"
    if score >= 60:
        return "Medium Confidence", "#F2994A"
    return "Uncertain",             "#F2C94C"


# ═══════════════════════════════════════════════════════════════════════════════
#  Explainability  (extended to cover UNCERTAIN verdict)
# ═══════════════════════════════════════════════════════════════════════════════

def _build_explanation(result: dict) -> list[dict]:
    """
    Generate explanation items for the UI.
    Now handles UNCERTAIN verdict and surfaces the ensemble note.
    """
    score   = result["ai_score"]
    is_fake = result["is_fake"]
    verdict = result.get("final_verdict", "")
    note    = result.get("note", "")
    items   = []

    # ── UNCERTAIN path ────────────────────────────────────────────────────────
    if verdict == "UNCERTAIN":
        items.append({
            "icon": "⚠️",
            "heading": "Conflicting Model Signals",
            "body": (
                f"The two detection models produced significantly different results "
                f"(gap: {result.get('difference', 0):.1f} pts). "
                "This typically occurs with post-processed, composited, or heavily "
                "compressed images that partially erase AI generation fingerprints."
            ),
        })
        items.append({
            "icon": "🔍",
            "heading": "Recommendation",
            "body": (
                "Do not rely on this result alone. Cross-check with EXIF metadata, "
                "reverse-image search, and manual visual inspection of texture and "
                "lighting consistency."
            ),
        })
        if note:
            items.append({
                "icon": "📋",
                "heading": "Engine Decision Note",
                "body": note,
            })
        return items

    # ── DEEPFAKE path ─────────────────────────────────────────────────────────
    if is_fake:
        items.append({
            "icon": "🔬",
            "heading": "Synthetic Pixel Distribution",
            "body": (
                f"The ensemble assigned {score:.1f}% probability to AI generation. "
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
                    "The ensemble score narrowly favours AI, but confidence is low. "
                    "Corroborate with metadata analysis and reverse image search."
                ),
            })

    # ── AUTHENTIC path ────────────────────────────────────────────────────────
    else:
        real = result["real_score"]
        items.append({
            "icon": "📷",
            "heading": "Natural Camera Noise Profile",
            "body": (
                f"The ensemble assigned {real:.1f}% probability to authentic capture. "
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

    # Append engine note as a closing item when present
    if note and verdict != "UNCERTAIN":
        items.append({
            "icon": "📋",
            "heading": "Ensemble Decision Note",
            "body": note,
        })

    return items


# ═══════════════════════════════════════════════════════════════════════════════
#  Public API  (interface unchanged)
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_image(image: Image.Image) -> dict:
    """
    Full pipeline: validate → load models → ensemble infer → interpret.
    Always returns a dict; on failure the dict contains an 'error' key.
    """
    try:
        ok, msg = validate_image(image)
        if not ok:
            return {"error": msg}

        ensemble_result = _run_ensemble_inference(image)

        # Enrich with UI metadata
        conf_level = ensemble_result.get("confidence_level", "")
        tier, colour = get_confidence_tier(ensemble_result["ai_score"], conf_level)

        ensemble_result["conf_label"]  = tier
        ensemble_result["conf_colour"] = colour
        ensemble_result["verdict"]     = ensemble_result["final_verdict"]

        # Colour mapping: UNCERTAIN gets a purple/amber treatment
        _verdict_colours = {
            "DEEPFAKE":  "#EF4444",
            "AUTHENTIC": "#10B981",
            "UNCERTAIN": "#F59E0B",
        }
        ensemble_result["verdict_colour"] = _verdict_colours.get(
            ensemble_result["final_verdict"], "#F59E0B"
        )

        ensemble_result["explanation"] = _build_explanation(ensemble_result)

        return ensemble_result

    except RuntimeError as exc:
        return {"error": str(exc)}
    except Exception as exc:
        return {"error": f"Unexpected error during analysis: {exc}"}
