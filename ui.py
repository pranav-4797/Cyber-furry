"""
ui.py — CyberFury AI Forensic Lab
All visual components: theme injection, progress stages, verdict card,
explainability panel, metadata viewer, and forensic tools bar.

REDESIGNED: Premium SaaS dashboard aesthetic — clean hierarchy, modular card system,
smooth gradients, polished typography (Rajdhani + DM Mono + DM Sans).

UI v2: Handles new UNCERTAIN verdict state, disagreement warning banner,
confidence-level badges (HIGH / MEDIUM / LOW), and per-model confidence display.
"""

import streamlit as st
import textwrap
import urllib.parse

# ═══════════════════════════════════════════════════════════════════════════════
#  Design Tokens
# ═══════════════════════════════════════════════════════════════════════════════

T = {
    # Backgrounds
    "bg":           "#080E1A",   # near-black base
    "surface":      "#0D1829",   # card background
    "surface2":     "#111F35",   # elevated card
    "overlay":      "#162340",   # hover / overlay

    # Borders
    "border":       "#1A2E4A",
    "border2":      "#223A5E",

    # Brand
    "accent":       "#2563EB",   # primary blue
    "accent_light": "#3B82F6",
    "cyan":         "#06B6D4",
    "cyan_dim":     "#0E7490",

    # Semantic
    "danger":       "#EF4444",
    "danger_dim":   "#7F1D1D",
    "success":      "#10B981",
    "success_dim":  "#064E3B",
    "warning":      "#F59E0B",
    "warning_dim":  "#78350F",
    "uncertain":    "#A78BFA",   # purple — used for UNCERTAIN verdict
    "uncertain_bg": "#1E1535",  # dark purple surface for uncertain cards

    # Typography
    "text":         "#F0F6FF",
    "text2":        "#A8BCCF",
    "muted":        "#546E8A",
}

# ═══════════════════════════════════════════════════════════════════════════════
#  Helper: CSS building blocks
# ═══════════════════════════════════════════════════════════════════════════════

def _card(content: str, accent_colour: str = "", extra_style: str = "") -> str:
    """Wrap content in a standard dashboard card."""
    border_col = accent_colour if accent_colour else T["border"]
    top_line   = (f"background:linear-gradient(90deg,{accent_colour},{T['cyan']});"
                  if accent_colour else
                  f"background:linear-gradient(90deg,{T['accent']},{T['cyan']});")
    return f"""
    <div style="
        background:{T['surface']};
        border:1px solid {border_col}55;
        border-radius:16px;
        padding:24px 26px;
        box-shadow:0 4px 32px rgba(0,0,0,0.45);
        margin-bottom:16px;
        position:relative;
        overflow:hidden;
        {extra_style}
    ">
        <div style="position:absolute;top:0;left:0;right:0;height:2px;{top_line}"></div>
        {content}
    </div>"""


def _label(text: str, style: str = "") -> str:
    """Uppercase micro-label (section headings, field names)."""
    return (f"<p style='margin:0 0 6px;color:{T['muted']};font-size:0.70rem;"
            f"text-transform:uppercase;letter-spacing:.14em;font-family:DM Sans,sans-serif;"
            f"{style}'>{text}</p>")


def _badge(text: str, colour: str, size: str = "0.72rem") -> str:
    """Pill-shaped badge."""
    return (f"<span style='display:inline-block;background:{colour}22;color:{colour};"
            f"border:1px solid {colour}44;padding:3px 11px;border-radius:100px;"
            f"font-size:{size};font-weight:700;letter-spacing:.08em;"
            f"font-family:DM Mono,monospace;'>{text}</span>")


def _progress_bar(pct: float, colour: str, height: str = "10px",
                  track_colour: str = "") -> str:
    """Rounded gradient progress bar."""
    track = track_colour or T["bg"]
    return f"""
    <div style="background:{track};height:{height};border-radius:99px;overflow:hidden;margin:8px 0;">
        <div style="
            width:{pct:.1f}%;height:100%;border-radius:99px;
            background:linear-gradient(90deg,{colour}99,{colour});
            transition:width 0.8s cubic-bezier(.4,0,.2,1);
        "></div>
    </div>"""


def _section_title(icon: str, text: str) -> None:
    """Render a consistent section header via st.markdown."""
    st.markdown(
        f"<p style='color:{T['cyan']};font-family:Rajdhani,sans-serif;"
        f"font-size:1.0rem;font-weight:700;letter-spacing:.1em;"
        f"text-transform:uppercase;margin:20px 0 12px;'>"
        f"{icon}&nbsp; {text}</p>",
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  Global Theme
# ═══════════════════════════════════════════════════════════════════════════════

def apply_theme() -> None:
    """Inject global CSS into the Streamlit app."""
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500;600&family=Rajdhani:wght@500;600;700&display=swap');

    /* ── Base ────────────────────────────────────────────────────────────── */
    .stApp {{
        background: radial-gradient(ellipse at 20% 0%, #0D1829 0%, {T['bg']} 60%);
        color: {T['text']};
        font-family: 'DM Sans', -apple-system, sans-serif;
    }}

    /* ── Global heading override ─────────────────────────────────────────── */
    h1, h2, h3, h4 {{
        color: {T['text']} !important;
        font-family: 'Rajdhani', sans-serif !important;
        font-weight: 700 !important;
    }}

    /* ── Sidebar ─────────────────────────────────────────────────────────── */
    [data-testid="stSidebar"] {{
        background: {T['surface']};
        border-right: 1px solid {T['border']};
    }}

    /* ── File uploader ───────────────────────────────────────────────────── */
    [data-testid="stFileUploader"] {{
        background: {T['surface']};
        padding: 22px;
        border-radius: 16px;
        border: 1.5px dashed {T['accent_light']};
        transition: border-color 0.25s, box-shadow 0.25s;
    }}
    [data-testid="stFileUploader"]:hover {{
        border-color: {T['cyan']};
        box-shadow: 0 0 0 3px {T['cyan']}18;
    }}
    [data-testid="stFileUploader"] section button {{
        color: #fff !important;
        background: {T['accent']} !important;
        border: none !important;
        border-radius: 8px !important;
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 600 !important;
    }}
    [data-testid="stFileUploader"] label,
    [data-testid="stFileUploader"] p,
    [data-testid="stFileUploader"] small {{ color: {T['text2']} !important; }}

    /* ── Primary button ──────────────────────────────────────────────────── */
    .stButton > button {{
        width: 100%;
        background: linear-gradient(135deg, {T['accent']}, {T['accent_light']});
        color: #fff;
        border: none;
        border-radius: 12px;
        font-family: 'Rajdhani', sans-serif;
        font-size: 1.05rem;
        font-weight: 700;
        letter-spacing: 0.1em;
        padding: 14px 20px;
        transition: all 0.22s ease;
        box-shadow: 0 4px 18px rgba(37,99,235,0.30);
    }}
    .stButton > button:hover {{
        background: linear-gradient(135deg, {T['cyan']}, {T['accent']});
        color: {T['bg']};
        transform: translateY(-2px);
        box-shadow: 0 8px 28px rgba(6,182,212,0.38);
    }}
    .stButton > button:active {{ transform: translateY(0); }}

    /* ── Link buttons ────────────────────────────────────────────────────── */
    [data-testid="stLinkButton"] a {{
        background: {T['surface2']} !important;
        color: {T['cyan']} !important;
        border: 1px solid {T['border2']} !important;
        border-radius: 10px !important;
        font-size: 0.83rem !important;
        font-weight: 600 !important;
        transition: all 0.2s !important;
        display: block; text-align: center;
    }}
    [data-testid="stLinkButton"] a:hover {{
        border-color: {T['cyan']} !important;
        background: rgba(6,182,212,0.08) !important;
        transform: translateY(-1px);
    }}

    /* ── Progress bar (Streamlit native) ────────────────────────────────── */
    [data-testid="stProgress"] > div > div {{
        background: linear-gradient(90deg, {T['accent']}, {T['cyan']});
        border-radius: 6px;
    }}
    [data-testid="stProgress"] > div {{
        background: {T['surface2']};
        border-radius: 6px;
    }}

    /* ── Expander ────────────────────────────────────────────────────────── */
    [data-testid="stExpander"] {{
        background: {T['surface']};
        border: 1px solid {T['border']} !important;
        border-radius: 12px;
        overflow: hidden;
        margin-bottom: 10px;
    }}
    [data-testid="stExpander"] summary {{
        font-family: 'Rajdhani', sans-serif;
        font-weight: 600;
        font-size: 0.93rem;
        color: {T['cyan']};
        padding: 10px 16px;
    }}

    /* ── Divider ─────────────────────────────────────────────────────────── */
    hr {{ border-color: {T['border']} !important; margin: 22px 0 !important; }}

    /* ── Code / mono ─────────────────────────────────────────────────────── */
    code {{ font-family: 'DM Mono', monospace; font-size: 0.81rem; }}

    /* ── Scrollbar ───────────────────────────────────────────────────────── */
    ::-webkit-scrollbar {{ width: 5px; height: 5px; }}
    ::-webkit-scrollbar-track {{ background: {T['bg']}; }}
    ::-webkit-scrollbar-thumb {{ background: {T['border2']}; border-radius: 4px; }}

    /* ── Alert boxes ─────────────────────────────────────────────────────── */
    [data-testid="stAlert"] {{ border-radius: 12px !important; }}

    /* ── Reusable utility classes ────────────────────────────────────────── */
    .cf-mono {{
        font-family: 'DM Mono', monospace;
        font-size: 0.81rem;
        color: {T['cyan']};
    }}
    .cf-muted {{
        color: {T['muted']};
        font-size: 0.85rem;
        font-family: 'DM Sans', sans-serif;
    }}
    .cf-value {{
        color: {T['text']};
        font-weight: 600;
        font-size: 0.88rem;
        font-family: 'DM Mono', monospace;
    }}
    </style>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  Header
# ═══════════════════════════════════════════════════════════════════════════════

def render_header() -> None:
    st.markdown(f"""
    <div style="text-align:center; padding:8px 0 32px;">
        <div style="display:inline-flex;align-items:center;gap:12px;margin-bottom:6px;">
            <div style="width:36px;height:36px;background:linear-gradient(135deg,{T['accent']},{T['cyan']});
                        border-radius:10px;display:flex;align-items:center;justify-content:center;
                        font-size:18px;box-shadow:0 4px 16px {T['accent']}55;">🛡️</div>
            <h1 style="
                font-family:'Rajdhani',sans-serif !important;
                font-size:2.2rem;
                font-weight:700;
                letter-spacing:.14em;
                margin:0;
                background:linear-gradient(90deg,{T['cyan']},{T['accent_light']},{T['text']});
                -webkit-background-clip:text;
                -webkit-text-fill-color:transparent;
                background-clip:text;
            ">CYBERFURY</h1>
        </div>
        <p style="color:{T['muted']};font-family:'DM Sans',sans-serif;font-size:0.80rem;
                  letter-spacing:.22em;margin:0;text-transform:uppercase;">
            AI Image Forensic Detection Lab
        </p>
        <div style="width:60px;height:1px;background:linear-gradient(90deg,transparent,{T['cyan']},transparent);
                    margin:12px auto 0;"></div>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  Scan Progress
# ═══════════════════════════════════════════════════════════════════════════════

SCAN_STAGES = [
    (0.10, "Initialising engine…"),
    (0.30, "Loading detection models…"),
    (0.55, "Pre-processing image…"),
    (0.75, "Running AI detection…"),
    (0.90, "Analysing metadata…"),
    (1.00, "Generating report…"),
]

STAGE_ICONS = ["⚙️", "📦", "🖼️", "🧠", "🔍", "📋"]


def run_with_progress(image, scan_fn, meta_fn):
    """Orchestrate the scan with a styled live progress bar."""
    bar    = st.progress(0.0)
    status = st.empty()

    def _step(pct: float, icon: str, label: str):
        bar.progress(pct)
        status.markdown(
            f"<div style='display:flex;align-items:center;gap:10px;padding:8px 0;'>"
            f"<span style='font-size:1rem;'>{icon}</span>"
            f"<span style='color:{T['cyan']};font-family:DM Mono,monospace;font-size:0.82rem;"
            f"letter-spacing:.04em;'>{label}</span>"
            f"<span style='color:{T['muted']};font-family:DM Mono,monospace;font-size:0.75rem;"
            f"margin-left:auto;'>{int(pct*100)}%</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

    for i, (pct, lbl) in enumerate(SCAN_STAGES[:2]):
        _step(pct, STAGE_ICONS[i], lbl)

    model_result = scan_fn(image)

    for i, (pct, lbl) in enumerate(SCAN_STAGES[2:4], start=2):
        _step(pct, STAGE_ICONS[i], lbl)

    meta_result = meta_fn(image)

    for i, (pct, lbl) in enumerate(SCAN_STAGES[4:], start=4):
        _step(pct, STAGE_ICONS[i], lbl)

    bar.empty()
    status.empty()
    return model_result, meta_result


# ═══════════════════════════════════════════════════════════════════════════════
#  Hero Verdict Card  [REDESIGNED]
# ═══════════════════════════════════════════════════════════════════════════════

def render_verdict_card(result: dict) -> None:
    """
    Hero verdict card — handles DEEPFAKE / AUTHENTIC / UNCERTAIN verdicts.

    v2 changes
    ----------
    • Reads confidence_level (HIGH / MEDIUM / LOW) from the ensemble engine
    • Renders a distinct UNCERTAIN state with warning styling and score gap display
    • Shows HIGH/MEDIUM/LOW badge instead of raw score tier label
    • High-risk banner only for HIGH-confidence DEEPFAKE results
    """
    score   = result["ai_score"]
    real    = result["real_score"]
    colour  = result["verdict_colour"]
    verdict = result["verdict"]
    tier    = result["conf_label"]

    conf_level = result.get("confidence_level", "")
    is_uncertain = verdict == "UNCERTAIN"

    # ── Contextual icon ───────────────────────────────────────────────────────
    _icons = {"DEEPFAKE": "⚠️", "AUTHENTIC": "✅", "UNCERTAIN": "❓"}
    verdict_icon = _icons.get(verdict, "🔍")

    # ── Confidence level badge (HIGH / MEDIUM / LOW) ──────────────────────────
    _conf_colours = {
        "HIGH":   T["danger"]   if verdict == "DEEPFAKE" else T["success"],
        "MEDIUM": T["warning"],
        "LOW":    T["uncertain"],
    }
    conf_badge_colour = _conf_colours.get(conf_level, T["warning"])
    conf_badge_text   = conf_level if conf_level else tier

    # ── Sub-label below verdict name ──────────────────────────────────────────
    _sublabels = {
        "DEEPFAKE":  "AI-generated content detected",
        "AUTHENTIC": "Authentic image — no AI signatures found",
        "UNCERTAIN": "Models disagree — result may be unreliable",
    }
    sublabel = _sublabels.get(verdict, "Ensemble detection result")

    # ── Score gap (shown on UNCERTAIN) ───────────────────────────────────────
    diff = result.get("difference", 0.0)
    diff_row = ""
    if is_uncertain and diff > 0:
        diff_row = f"""
        <div style="display:inline-flex;align-items:center;gap:8px;
                    background:{T['warning']}18;border:1px solid {T['warning']}33;
                    border-radius:8px;padding:5px 12px;margin-top:10px;">
            <span style="color:{T['warning']};font-size:0.78rem;font-weight:700;">
                Score Gap
            </span>
            <span class="cf-mono" style="color:{T['warning']};">{diff:.1f} pts</span>
        </div>"""

    # ── Progress bar track colour ─────────────────────────────────────────────
    bar_track = T["uncertain_bg"] if is_uncertain else T["surface2"]

    inner = f"""
    <!-- Header row: label + confidence badge -->
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
        {_label('Analysis Verdict')}
        {_badge(conf_badge_text, conf_badge_colour, "0.70rem")}
    </div>

    <!-- Large verdict text block -->
    <div style="text-align:center;padding:8px 0 16px;">
        <div style="font-size:3rem;margin-bottom:4px;">{verdict_icon}</div>
        <h2 style="
            color:{colour} !important;
            font-family:'Rajdhani',sans-serif !important;
            font-size:2.5rem;
            font-weight:700;
            letter-spacing:.12em;
            margin:0;
            text-shadow:0 0 40px {colour}44;
        ">{verdict}</h2>
        <p style="color:{T['text2']};font-size:0.82rem;margin:5px 0 0;letter-spacing:.04em;">
            {sublabel}
        </p>
        {diff_row}
    </div>

    <!-- Probability meter -->
    {_label('Synthetic Probability', 'margin-top:8px;')}
    {_progress_bar(score, colour, '12px', bar_track)}
    <div style="display:flex;justify-content:space-between;margin-top:5px;">
        <span class="cf-mono" style="color:{colour};">AI &nbsp;{score:.1f}%</span>
        <span class="cf-mono" style="color:{T['success']};">Real {real:.1f}%</span>
    </div>
    """

    st.markdown(_card(inner, colour), unsafe_allow_html=True)

    # ── UNCERTAIN warning banner ───────────────────────────────────────────────
    if is_uncertain:
        note = result.get("note", "")
        st.markdown(f"""
        <div style="
            background:rgba(245,158,11,0.08);
            border:1px solid {T['warning']}55;
            border-left:4px solid {T['warning']};
            border-radius:0 12px 12px 0;
            padding:14px 18px;
            margin-top:-8px;
            margin-bottom:14px;
        ">
            <p style="margin:0 0 5px;color:{T['warning']};font-weight:700;font-size:0.90rem;">
                ⚠️ Models disagree significantly
            </p>
            <p style="margin:0;color:{T['text2']};font-size:0.83rem;line-height:1.6;">
                This may be a post-processed, composited, or edge-case image.
                Do not rely on this result alone — corroborate with metadata and
                manual inspection.
            </p>
            {f'<p style="margin:8px 0 0;color:{T["muted"]};font-size:0.77rem;font-style:italic;">{note}</p>' if note else ''}
        </div>
        """, unsafe_allow_html=True)

    # ── High-risk banner (DEEPFAKE, HIGH confidence only) ────────────────────
    elif verdict == "DEEPFAKE" and conf_level == "HIGH":
        st.markdown(f"""
        <div style="
            background:rgba(239,68,68,0.07);
            border:1px solid {T['danger']}44;
            border-radius:12px;
            padding:11px 16px;
            margin-top:-8px;
            margin-bottom:14px;
            display:flex;align-items:center;gap:10px;
        ">
            <span style="font-size:1rem;">🚩</span>
            <span style="color:{T['danger']};font-weight:600;font-size:0.86rem;">High Risk</span>
            <span style="color:{T['text2']};font-size:0.83rem;">
                Strong synthetic-generation signatures detected — both models in agreement.
            </span>
        </div>
        """, unsafe_allow_html=True)

    # ── Probability breakdown (collapsible) ───────────────────────────────────
    with st.expander("📊 Full Probability Breakdown"):
        for lbl, pct in result.get("all_scores", {}).items():
            bar_col = T["danger"] if any(k in lbl.lower() for k in ("artif","fake","ai")) else T["success"]
            st.markdown(f"""
            <div style="margin-bottom:12px;">
                <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                    <span class="cf-value">{lbl}</span>
                    <span class="cf-mono">{pct:.2f}%</span>
                </div>
                {_progress_bar(pct, bar_col, '7px', T['surface2'])}
            </div>
            """, unsafe_allow_html=True)

    # ── Ensemble comparison (only when secondary model ran) ───────────────────
    if result.get("has_secondary"):
        render_ensemble_comparison(result)


# ═══════════════════════════════════════════════════════════════════════════════
#  Ensemble Model Comparison  [REDESIGNED — new premium layout]
# ═══════════════════════════════════════════════════════════════════════════════

def _model_card_html(model: dict, is_uncertain: bool = False) -> str:
    """
    Build the inner HTML for a single model comparison card.
    Shows per-model confidence score when available (new field from model.py v2).
    """
    ai_pct   = model["ai_score"]
    real_pct = model["real_score"]
    is_fake  = ai_pct > 50.0
    colour   = T["uncertain"] if is_uncertain else (T["danger"] if is_fake else T["success"])
    verdict  = "UNCERTAIN" if is_uncertain else ("DEEPFAKE" if is_fake else "AUTHENTIC")

    raw_name = model["name"]
    role     = raw_name.split(" (")[0]
    sub_name = raw_name.split("(")[-1].rstrip(")")

    # Per-model confidence (new field) — shown as a small pill
    model_conf = model.get("confidence", None)
    conf_pill  = ""
    if model_conf is not None:
        conf_col = T["success"] if model_conf >= 80 else T["warning"] if model_conf >= 60 else T["muted"]
        conf_pill = (
            f"<span style='font-family:DM Mono,monospace;font-size:0.68rem;"
            f"color:{conf_col};background:{conf_col}18;border:1px solid {conf_col}33;"
            f"border-radius:6px;padding:2px 7px;margin-left:8px;'>"
            f"conf {model_conf:.0f}%</span>"
        )

    return f"""
    <div style="position:absolute;top:0;left:0;right:0;height:2px;
                background:linear-gradient(90deg,{colour},{colour}44);"></div>

    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px;">
        <div>
            {_label(role + ' model')}
            <p style="margin:0;color:{T['text2']};font-size:0.71rem;
                      font-family:'DM Mono',monospace;letter-spacing:.03em;">
                {sub_name}
            </p>
        </div>
        <div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px;">
            {_badge(verdict, colour, "0.67rem")}
            {conf_pill}
        </div>
    </div>

    <div style="text-align:center;padding:4px 0 12px;">
        <span style="font-family:'Rajdhani',sans-serif;font-size:2.3rem;
                     font-weight:700;color:{colour};letter-spacing:.04em;">
            {ai_pct:.1f}%
        </span>
        <p style="margin:2px 0 0;color:{T['muted']};font-size:0.70rem;
                  letter-spacing:.1em;text-transform:uppercase;">AI Score</p>
    </div>

    {_progress_bar(ai_pct, colour, '6px', T['bg'])}

    <p style="margin:5px 0 0;text-align:right;color:{T['text2']};
              font-family:'DM Mono',monospace;font-size:0.73rem;">
        Real &nbsp;{real_pct:.1f}%
    </p>
    """


def render_ensemble_comparison(result: dict) -> None:
    """
    Side-by-side model cards with agreement indicator and engine decision info.

    v2 changes
    ----------
    • Agreement indicator now shows score gap (difference) explicitly
    • UNCERTAIN state gets a distinct orange/amber treatment throughout
    • Engine path note displayed below the comparison
    • Weighted score bar shows actual weights used (not hardcoded 60/40)
    • Per-model confidence pills sourced from new model.py confidence field
    """
    models = result.get("models", [])
    if len(models) < 2:
        return

    _section_title("⚖️", "Ensemble Model Comparison")

    agreement    = result.get("agreement", True)
    diff         = result.get("difference", 0.0)
    conf_level   = result.get("confidence_level", "MEDIUM")
    final_verdict = result.get("final_verdict", "")
    is_uncertain  = final_verdict == "UNCERTAIN"
    note          = result.get("note", "")
    weights_used  = result.get("weights_used", (0.6, 0.4))

    # ── Agreement / Disagreement indicator ───────────────────────────────────
    if is_uncertain:
        agree_colour  = T["warning"]
        agree_icon    = "⚠️"
        agree_heading = f"Strong Disagreement — {diff:.1f} pt gap"
        agree_body    = ("The models landed on opposite sides of the detection boundary. "
                         "Verdict set to UNCERTAIN. Manual review is required.")
    elif agreement:
        agree_colour  = T["success"]
        agree_icon    = "✅"
        agree_heading = f"Models Agree  ·  Gap {diff:.1f} pts"
        agree_body    = f"{conf_level.title()} confidence — weighted ensemble applied."
    else:
        agree_colour  = T["warning"]
        agree_icon    = "⚠️"
        agree_heading = f"Weak Agreement  ·  Gap {diff:.1f} pts"
        agree_body    = ("Models lean the same direction but differ in magnitude. "
                         "Confidence reduced accordingly.")

    st.markdown(f"""
    <div style="
        background:linear-gradient(135deg,{agree_colour}10,{agree_colour}05);
        border:1px solid {agree_colour}44;
        border-left:4px solid {agree_colour};
        border-radius:0 12px 12px 0;
        padding:14px 18px;
        margin-bottom:18px;
        display:flex;align-items:flex-start;gap:14px;
    ">
        <span style="font-size:1.25rem;line-height:1.2;">{agree_icon}</span>
        <div>
            <p style="margin:0 0 4px;font-weight:700;color:{agree_colour};font-size:0.90rem;">
                {agree_heading}
            </p>
            <p style="margin:0;color:{T['text2']};font-size:0.81rem;line-height:1.55;">
                {agree_body}
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Side-by-side model cards ──────────────────────────────────────────────
    col_a, col_b = st.columns(2, gap="medium")

    for col, model_idx in ((col_a, 0), (col_b, 1)):
        m      = models[model_idx]
        ai_pct = m["ai_score"]
        # For uncertain, highlight both cards in amber
        if is_uncertain:
            border_col = T["warning"]
        else:
            border_col = T["danger"] if ai_pct > 50 else T["success"]
        with col:
            st.markdown(f"""
            <div style="
                background:{T['surface']};
                border:1px solid {border_col}44;
                border-radius:14px;
                padding:20px 20px 16px;
                box-shadow:0 4px 20px rgba(0,0,0,0.4);
                position:relative;overflow:hidden;
            ">{_model_card_html(m, is_uncertain=is_uncertain)}</div>
            """, unsafe_allow_html=True)

    # ── Ensemble score bar + weights used ────────────────────────────────────
    final_ai  = result.get("final_ai_score", result.get("ai_score", 0))
    bar_colour = T["warning"] if is_uncertain else T["accent_light"]
    pw, sw     = weights_used
    weight_label = (
        f"Ensemble Score  ·  {pw*100:.0f}% primary / {sw*100:.0f}% secondary"
        if not is_uncertain else
        "Uncertainty-adjusted Score (not a simple average)"
    )

    st.markdown(f"""
    <div style="
        background:{T['surface2']};border:1px solid {T['border2']};
        border-radius:12px;padding:16px 20px;margin-top:6px;
    ">
        {_label(weight_label)}
        {_progress_bar(final_ai, bar_colour, '8px', T['bg'])}
        <div style="display:flex;justify-content:space-between;margin-top:3px;">
            <span class="cf-mono" style="color:{bar_colour};">AI {final_ai:.1f}%</span>
            <span class="cf-mono" style="color:{T['success']};">Real {100-final_ai:.1f}%</span>
        </div>
        {f'<p style="margin:10px 0 0;color:{T[chr(34)]+"muted"+chr(34)};font-size:0.76rem;font-style:italic;">{note}</p>' if note else ''}
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  Explainability Panel  [REFINED]
# ═══════════════════════════════════════════════════════════════════════════════

def render_explainability(result: dict) -> None:
    """Render the explainability section."""
    _section_title("🧩", "Why This Prediction?")

    for item in result.get("explanation", []):
        st.markdown(f"""
        <div style="
            background:{T['surface2']};
            border-left:3px solid {T['accent']};
            padding:13px 16px;
            margin-bottom:10px;
            border-radius:0 10px 10px 0;
            transition:background 0.2s;
        ">
            <p style="margin:0 0 5px;font-weight:600;color:{T['text']};
                      font-size:0.90rem;font-family:'Rajdhani',sans-serif;letter-spacing:.03em;">
                {item['icon']}&nbsp; {item['heading']}
            </p>
            <p style="margin:0;color:{T['text2']};font-size:0.83rem;line-height:1.6;">
                {item['body']}
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(
        f"<p style='color:{T['muted']};font-size:0.76rem;margin-top:6px;font-style:italic;'>"
        f"⚠️ AI detection is probabilistic. Always corroborate with metadata and reverse-image analysis.</p>",
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  Metadata Panel  [REFINED]
# ═══════════════════════════════════════════════════════════════════════════════

_SEVERITY_CONFIG = {
    "critical": (T["danger"],  "🚨"),
    "warning":  (T["warning"], "⚠️"),
    "info":     (T["cyan"],    "ℹ️"),
}


def render_metadata_panel(meta: dict) -> None:
    """Render structured metadata forensics."""
    _section_title("🛠️", "Metadata Forensics")

    # Summary strip
    st.markdown(
        f"<p style='color:{T['text2']};font-size:0.87rem;margin-bottom:14px;'>"
        f"{meta['summary']}</p>",
        unsafe_allow_html=True,
    )

    # Anomaly cards
    for anom in meta.get("anomalies", []):
        col, icon = _SEVERITY_CONFIG.get(anom["severity"], (T["muted"], "•"))
        st.markdown(f"""
        <div style="
            background:{col}0D;
            border:1px solid {col}33;
            border-radius:10px;
            padding:11px 15px;
            margin-bottom:8px;
        ">
            <p style="margin:0 0 3px;font-size:0.87rem;font-weight:700;color:{col};">
                {icon}&nbsp; {anom['label']}
            </p>
            <p style="margin:0;font-size:0.81rem;color:{T['text2']};line-height:1.55;">
                {anom['detail']}
            </p>
        </div>
        """, unsafe_allow_html=True)

    # Structured fields (camera / software / timestamps)
    has_structured = any([
        meta.get("camera_info"),
        meta.get("software_info"),
        meta.get("timestamp_info"),
    ])

    if has_structured:
        with st.expander("📋 Structured Metadata Fields"):
            for title, data in [
                ("📷 Camera",     meta.get("camera_info",    {})),
                ("💾 Software",   meta.get("software_info",  {})),
                ("🕐 Timestamps", meta.get("timestamp_info", {})),
            ]:
                if data:
                    st.markdown(
                        f"<p style='color:{T['cyan']};font-size:0.83rem;"
                        f"font-weight:700;margin:10px 0 6px;'>{title}</p>",
                        unsafe_allow_html=True,
                    )
                    for k, v in data.items():
                        st.markdown(
                            f"<div style='display:flex;gap:10px;margin-bottom:4px;"
                            f"padding-bottom:4px;border-bottom:1px solid {T['border']};'>"
                            f"<span class='cf-muted' style='min-width:160px;flex-shrink:0;'>{k}</span>"
                            f"<span class='cf-value'>{v}</span></div>",
                            unsafe_allow_html=True,
                        )

    # Raw EXIF dump
    raw = meta.get("raw", {})
    if raw:
        with st.expander(f"🗄️ Raw EXIF Dump ({len(raw)} fields)"):
            for k, v in raw.items():
                st.markdown(
                    f"<div style='display:flex;gap:10px;margin-bottom:3px;"
                    f"padding-bottom:3px;border-bottom:1px solid {T['border']};'>"
                    f"<span class='cf-muted' style='min-width:180px;flex-shrink:0;'>{k}</span>"
                    f"<span class='cf-mono' style='color:{T['text2']};word-break:break-all;'>"
                    f"{v[:120]}</span></div>",
                    unsafe_allow_html=True,
                )


# ═══════════════════════════════════════════════════════════════════════════════
#  Forensic Tools Bar  [REFINED]
# ═══════════════════════════════════════════════════════════════════════════════

def render_forensic_tools(filename: str) -> None:
    """External investigation shortcut buttons."""
    st.markdown("---")
    _section_title("🔗", "External Investigation Tools")
    query = urllib.parse.quote(f'"{filename}"')
    c1, c2, c3 = st.columns(3)
    with c1:
        st.link_button("📂 Filename Search",
                        f"https://www.google.com/search?q={query}",
                        use_container_width=True)
    with c2:
        st.link_button("🔍 Google Lens",
                        "https://lens.google.com/upload",
                        use_container_width=True)
    with c3:
        st.link_button("🌐 TinEye",
                        "https://tineye.com/",
                        use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  Reset Button
# ═══════════════════════════════════════════════════════════════════════════════

def render_reset_button() -> None:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔁 Scan Another Image"):
        for key in ["scan_result", "scan_meta", "scan_filename"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
#  Idle Placeholder  [REDESIGNED]
# ═══════════════════════════════════════════════════════════════════════════════

def render_idle_placeholder() -> None:
    st.markdown(f"""
    <div style="
        text-align:center;
        padding:70px 20px;
        border:1px dashed {T['border2']};
        border-radius:18px;
        margin-top:8px;
        background:radial-gradient(ellipse at 50% 30%, {T['surface']} 0%, {T['bg']} 100%);
    ">
        <div style="
            width:64px;height:64px;
            background:linear-gradient(135deg,{T['accent']}22,{T['cyan']}22);
            border-radius:18px;
            display:flex;align-items:center;justify-content:center;
            font-size:28px;margin:0 auto 18px;
            border:1px solid {T['border2']};
        ">🔬</div>
        <h3 style="color:{T['text2']} !important;font-family:'Rajdhani',sans-serif !important;
                   font-weight:600;letter-spacing:.06em;margin:0 0 10px;">
            System Ready
        </h3>
        <p style="font-size:0.85rem;color:{T['muted']};line-height:1.7;
                  max-width:240px;margin:0 auto;">
            Upload an image on the left, then click
            <span style='color:{T['cyan']};font-weight:600;'>Run Forensic Scan</span>
            to begin analysis.
        </p>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  Error Card
# ═══════════════════════════════════════════════════════════════════════════════

def render_error(message: str) -> None:
    st.markdown(f"""
    <div style="
        background:rgba(239,68,68,0.07);
        border:1px solid {T['danger']}55;
        border-radius:14px;
        padding:18px 22px;
        margin-top:12px;
        display:flex;
        gap:14px;
        align-items:flex-start;
    ">
        <span style="font-size:1.3rem;">⛔</span>
        <div>
            <p style="color:{T['danger']};font-weight:700;margin:0 0 5px;font-size:0.92rem;">
                Analysis Failed
            </p>
            <p style="color:{T['text2']};font-size:0.84rem;margin:0;line-height:1.55;">
                {message}
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)
