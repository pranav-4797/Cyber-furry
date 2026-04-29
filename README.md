# 🛡️ CyberFury — AI Forensic Lab

> **Detect AI-generated images with dual-model ensemble intelligence.**  
> A production-ready Streamlit application powered by Hugging Face Transformers and a five-path decision engine.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Usage](#usage)
- [Ensemble Decision Engine](#ensemble-decision-engine)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Output & Reports](#output--reports)
- [Performance](#performance)
- [Troubleshooting](#troubleshooting)
- [Disclaimer](#disclaimer)

---

## Overview

CyberFury is an AI forensic tool that determines whether an image was synthesised by an AI pipeline (Stable Diffusion, DALL·E, Midjourney, etc.) or captured by a real camera. It combines two fine-tuned image-classification transformers with a weighted ensemble strategy and deep EXIF metadata analysis to produce transparent, explainable verdicts.

---

## Features

### 🤖 Dual-Model Ensemble
- **Primary model** — `Organika/sdxl-detector` (base weight 60%)
- **Secondary model** — `umm-maybe/AI-image-detector` (base weight 40%)
- Dynamic weight adjustment based on per-model confidence
- Graceful fallback to primary-only mode if secondary is unavailable

### 🧠 Five-Path Decision Engine
| Path | Condition | Verdict | Confidence |
|------|-----------|---------|------------|
| A | Both models ≥ 70% AI | DEEPFAKE | HIGH |
| B | Both models ≤ 30% AI | AUTHENTIC | HIGH |
| C | One model ≥ 90% confident | Trust dominant model | MEDIUM |
| D | Same direction, moderate gap | Weighted average | MEDIUM |
| E | Opposite sides, gap ≥ 40 pts | UNCERTAIN | LOW |

### 🔍 Metadata Forensics
- Full EXIF extraction and structured display
- AI-tool fingerprint detection (Midjourney, DALL·E, Stable Diffusion, ComfyUI, etc.)
- Editing software detection (Photoshop, Lightroom, GIMP, etc.)
- Timestamp cross-validation (mismatch & future-date detection)
- GPS presence logging
- Anomaly severity scoring: `critical` · `warning` · `info`

### 📊 Explainability Panel
- Human-readable reasoning for every verdict
- Handles DEEPFAKE, AUTHENTIC, and UNCERTAIN paths distinctly
- Per-model individual score breakdown
- Agreement/disagreement badge between models

### 📥 Downloadable Reports
- **Plain-text (.txt)** — full forensic report with ASCII bar charts
- **Self-contained HTML (.html)** — styled report with embedded image thumbnail

### 🔗 External Investigation Tools
Quick-launch buttons for Google filename search, Google Lens, and TinEye reverse-image search.

---

## Architecture

```
app.py              ← Streamlit entrypoint; orchestrates all modules
│
├── model.py        ← Model loading, inference, ensemble engine, explainability
├── metadata.py     ← EXIF extraction, anomaly detection, software fingerprinting
├── ui.py           ← All visual components (theme, cards, panels, progress)
└── report_generator.py  ← TXT and HTML report generation
```

Data flows in one direction: `app.py` calls `analyze_image()` and `analyze_metadata()`, then passes the results to `ui.*` rendering functions and `report_generator.*` export functions.

---

## Installation

### Prerequisites
- Python 3.10+
- pip
- Internet access (for first-time model download from Hugging Face)
- Optional: CUDA-capable GPU for faster inference

### Steps

```bash
# 1. Clone or copy the project files
git clone <your-repo-url>
cd cyberfury

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
streamlit run app.py
```

The app will open at `http://localhost:8501` in your browser.

### Requirements

```
streamlit>=1.32.0
torch>=2.0.0
torchvision>=0.15.0
transformers>=4.38.0
accelerate>=0.26.0
Pillow>=10.0.0
urllib3>=2.0.0
```

---

## Usage

1. **Open the app** — `streamlit run app.py`
2. **Upload an image** — drag & drop or click the upload area (JPG, JPEG, PNG, WEBP; max 15 MB)
3. **(Optional) Pre-load models** — click ⚡ Pre-load Models in the sidebar to warm up both models before your first scan
4. **Run scan** — click 🚨 RUN FORENSIC SCAN
5. **Review results** — verdict card, per-model scores, explainability panel, and metadata anomalies
6. **Download report** — choose TXT or HTML format
7. **Investigate further** — use the external tool buttons (Google Lens, TinEye, filename search)

### Image Constraints
| Constraint | Limit |
|------------|-------|
| Formats | JPG, JPEG, PNG, WEBP |
| Max file size | 15 MB |
| Max dimensions | 4096 × 4096 px |
| Min dimensions | 32 × 32 px |

---

## Ensemble Decision Engine

### Dynamic Weight Adjustment

The base weights (60/40) are adjusted automatically before final scoring:

| Condition | Primary Weight | Secondary Weight |
|-----------|---------------|-----------------|
| Primary confidence ≥ 90% | 0.80 | 0.20 |
| Secondary confidence ≥ 90%, Primary < 70% | 0.30 | 0.70 |
| Default | 0.60 | 0.40 |

### Confidence Tiers
| Tier | Condition | Badge Colour |
|------|-----------|-------------|
| 🔴 High Confidence | Confidence level = HIGH | Red |
| 🟠 Medium Confidence | Confidence level = MEDIUM | Orange |
| 🟣 Uncertain | Confidence level = LOW | Purple |

### Verdict Colours
| Verdict | Colour |
|---------|--------|
| DEEPFAKE | `#EF4444` (red) |
| AUTHENTIC | `#10B981` (green) |
| UNCERTAIN | `#F59E0B` (amber) |

---

## Project Structure

```
cyberfury/
├── app.py               # Main Streamlit app (entry point)
├── model.py             # Ensemble inference, validation, explainability
├── metadata.py          # EXIF analysis and anomaly detection
├── ui.py                # UI components and design system
├── report_generator.py  # TXT and HTML report export
└── requirements.txt     # Python dependencies
```

### Module Responsibilities

**`model.py`**
- `load_primary_model()` — loads and caches `Organika/sdxl-detector`
- `load_secondary_model()` — loads and caches `umm-maybe/AI-image-detector`; returns `None` on failure
- `analyze_image(image)` — full pipeline: validate → infer → ensemble → explain
- `validate_image(image)` — dimension and colour mode checks

**`metadata.py`**
- `analyze_metadata(image)` — full EXIF forensic pass
- Returns: `raw`, `flags`, `anomalies`, `camera_info`, `software_info`, `timestamp_info`, `gps_info`, `summary`

**`ui.py`**
- `apply_theme()` — injects global CSS (Rajdhani + DM Mono + DM Sans typefaces)
- `render_verdict_card()` — main verdict with score meters
- `render_explainability()` — reasoning panel
- `render_metadata_panel()` — anomaly cards + EXIF dump
- `render_ensemble_comparison()` — side-by-side model scores with agreement badge
- `run_with_progress()` — staged progress bar during inference

**`report_generator.py`**
- `generate_text_report()` — UTF-8 plain-text report
- `generate_html_report()` — self-contained styled HTML report
- `image_to_data_uri()` — base64-encodes the image for HTML embedding

---

## Configuration

All tunable constants live at the top of `model.py`:

```python
# Model selection
PRIMARY_MODEL_ID   = "Organika/sdxl-detector"
SECONDARY_MODEL_ID = "umm-maybe/AI-image-detector"   # set "" to disable

# Base ensemble weights (must sum to 1.0)
PRIMARY_MODEL_WEIGHT   = 0.6
SECONDARY_MODEL_WEIGHT = 0.4

# Decision thresholds
_STRONG_AGREE_AI_THRESHOLD   = 70.0   # both ≥ this → DEEPFAKE HIGH
_STRONG_AGREE_REAL_THRESHOLD = 30.0   # both ≤ this → AUTHENTIC HIGH
_DISAGREEMENT_THRESHOLD      = 40.0   # score gap ≥ this → UNCERTAIN
_HIGH_CONFIDENCE_THRESHOLD   = 90.0   # triggers dynamic weight boost
_DOMINANT_CONFIDENCE         = 90.0   # single model trusted under disagreement

# Image constraints
MAX_PIXELS  = 4096
MIN_PIXELS  = 32
MAX_FILE_MB = 15
```

### Common Tweaks

**Trust primary model more:**
```python
PRIMARY_MODEL_WEIGHT   = 0.7
SECONDARY_MODEL_WEIGHT = 0.3
```

**Disable secondary model (primary-only mode):**
```python
SECONDARY_MODEL_ID = ""
```

**Swap in a different secondary model:**
```python
SECONDARY_MODEL_ID = "your-huggingface/model-id"
```

---

## Output & Reports

### `analyze_image()` Return Dict

```python
{
    # Core verdict
    "final_verdict":    "DEEPFAKE",      # "DEEPFAKE" | "AUTHENTIC" | "UNCERTAIN"
    "verdict":          "DEEPFAKE",      # alias (backward compat)
    "verdict_colour":   "#EF4444",

    # Scores
    "final_ai_score":       71.8,        # weighted ensemble AI probability
    "ai_score":             71.8,        # alias
    "ensemble_real_score":  28.2,
    "real_score":           28.2,        # alias

    # Confidence
    "confidence":           85.5,
    "confidence_level":     "HIGH",      # "HIGH" | "MEDIUM" | "LOW"
    "conf_label":           "High Confidence",
    "conf_colour":          "#EB5757",

    # Ensemble metadata
    "agreement":            True,        # models agree on direction?
    "has_secondary":        True,        # secondary model available?
    "difference":           6.7,         # gap between model scores
    "note":                 "...",       # engine decision explanation

    # Per-model breakdown
    "models": [
        {
            "name":       "Primary (Organika/sdxl-detector)",
            "ai_score":   75.2,
            "real_score": 24.8,
            "label":      "artificial"
        },
        {
            "name":       "Secondary (umm-maybe/AI-image-detector)",
            "ai_score":   68.5,
            "real_score": 31.5,
            "label":      "artificial"
        }
    ],

    # UI
    "explanation":      [...],           # list of {icon, heading, body}
    "predicted_label":  "artificial",
    "all_scores":       {"artificial": 75.2, "real": 24.8},
}
```

---

## Performance

| Metric | Value | Notes |
|--------|-------|-------|
| First scan | 50–70 s | Both models download + load + infer |
| Cached scans | 10–15 s | Models reused from Streamlit cache |
| Memory usage | ~2.5–3.5 GB | Both models in VRAM or RAM |
| Inference time | ~5–8 s | Per image after models are loaded |
| GPU acceleration | Auto | CUDA detected automatically |

---

## Troubleshooting

**"Secondary model unavailable"**  
Check the model ID spelling in `model.py`, verify your internet connection, or set `SECONDARY_MODEL_ID = ""` to run primary-only.

**Out of memory**  
Use a GPU (CUDA auto-detected). Alternatively, disable the secondary model or reduce image dimensions before uploading.

**Inference is very slow**  
The first scan is always slow — models are downloading and loading. Subsequent scans use the Streamlit cache and should be 4–6× faster. Ensure sufficient RAM or GPU memory is available.

**Agreement badge always shows "True"**  
This is normal when the secondary model is unavailable. Check the `has_secondary` field in the result dict, and verify the secondary model loaded in the sidebar.

**App won't start**  
Run `python -m py_compile model.py app.py ui.py` to check for syntax errors, then verify all packages in `requirements.txt` are installed.

---

## Disclaimer

> ⚠️ AI image detection is **probabilistic**, not deterministic. CyberFury should be used as **supporting evidence** alongside metadata analysis, reverse-image search, and expert review — not as the sole basis for any conclusion about image authenticity.

---

## Acknowledgements

- [Organika/sdxl-detector](https://huggingface.co/Organika/sdxl-detector) — Primary classification model
- [umm-maybe/AI-image-detector](https://huggingface.co/umm-maybe/AI-image-detector) — Secondary classification model
- [Hugging Face Transformers](https://github.com/huggingface/transformers) — Model hosting and inference framework
- [Streamlit](https://streamlit.io) — Web application framework

---

*CyberFury AI Forensic Lab — Built with PyTorch · Hugging Face · Streamlit*
