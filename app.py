"""
app.py — CyberFury AI Forensic Lab
Main Streamlit entrypoint.  Orchestrates UI, model inference, and report download.

Run with:
    streamlit run app.py
"""

import warnings
import streamlit as st
from PIL import Image

# ── Suppress non-critical transformer warnings ─────────────────────────────────
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# ── Page config (must be the very first Streamlit call) ────────────────────────
st.set_page_config(
    page_title  = "CyberFury | AI Forensic Lab",
    page_icon   = "🛡️",
    layout      = "wide",
    initial_sidebar_state = "collapsed",
)

# ── Internal modules ───────────────────────────────────────────────────────────
from model            import analyze_image, load_primary_model, load_secondary_model, MAX_FILE_MB
from metadata         import analyze_metadata
from report_generator import generate_text_report, generate_html_report, image_to_data_uri
import ui


# ═══════════════════════════════════════════════════════════════════════════════
#  Session-State Keys
# ═══════════════════════════════════════════════════════════════════════════════
_KEYS = ["scan_result", "scan_meta", "scan_filename", "scan_image"]

def _init_state():
    for key in _KEYS:
        if key not in st.session_state:
            st.session_state[key] = None


# ═══════════════════════════════════════════════════════════════════════════════
#  Sidebar — About & Settings
# ═══════════════════════════════════════════════════════════════════════════════
def _render_sidebar():
    with st.sidebar:
        st.markdown(f"""
        <div style="padding:10px 0;">
            <h2 style="font-family:'Rajdhani',sans-serif; letter-spacing:.08em; margin-bottom:4px;">
                ⚙️ About
            </h2>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        **CyberFury** uses an ensemble of fine-tuned image-classification transformers to determine
        whether an image was created by an AI system (Stable Diffusion, DALL·E, Midjourney, etc.)
        or captured by a real camera.

        **Primary Model:** `Organika/sdxl-detector`  
        **Secondary Model:** `umm-maybe/AI-image-detector`  
        **Framework:** Hugging Face Transformers + PyTorch  

        ---
        **Ensemble Strategy**  
        Weighted averaging (60% primary / 40% secondary) for robust consensus detection.
        If secondary model unavailable, gracefully falls back to primary.

        ---
        **Supported formats**  
        JPG · PNG · WEBP · JPEG  

        **Max file size**  
        15 MB

        ---
        **Confidence Tiers**  
        🔴 ≥ 90 % — High  
        🟠 60–89 % — Medium  
        🟡 < 60 % — Uncertain  

        ---
        ⚠️ *AI detection is probabilistic. Always corroborate with metadata and reverse-image search.*
        """)

        st.markdown("---")

        # Model warm-up toggle
        if st.button("⚡ Pre-load Models", help="Load both detection models into memory to speed up the first scan."):
            with st.spinner("Loading models…"):
                try:
                    load_primary_model()
                    secondary = load_secondary_model()
                    status_msg = "Both models loaded successfully!"
                    if secondary is None:
                        status_msg = "Primary model loaded. Secondary model unavailable (will use primary only)."
                    st.success(status_msg)
                except Exception as e:
                    st.error(f"Load failed: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
#  File Validation
# ═══════════════════════════════════════════════════════════════════════════════
def _validate_upload(file) -> tuple[bool, str]:
    """Validate uploaded file size and readability."""
    size_mb = len(file.getvalue()) / (1024 * 1024)
    if size_mb > MAX_FILE_MB:
        return False, f"File too large ({size_mb:.1f} MB). Maximum allowed: {MAX_FILE_MB} MB."
    try:
        img = Image.open(file)
        img.verify()    # check for corruption
    except Exception:
        return False, "File appears to be corrupted or is not a valid image."
    return True, "OK"


# ═══════════════════════════════════════════════════════════════════════════════
#  Download Section
# ═══════════════════════════════════════════════════════════════════════════════
def _render_downloads(filename: str, scan_result: dict, scan_meta: dict, image: Image.Image):
    """Render report download buttons."""
    st.markdown("---")
    st.markdown(
        "<h4 style='color:#56CCF2; font-family:Rajdhani,sans-serif; "
        "letter-spacing:.06em; margin-bottom:10px;'>📥 Download Forensic Report</h4>",
        unsafe_allow_html=True,
    )

    col_txt, col_html = st.columns(2)

    # Plain-text report
    text_report = generate_text_report(filename, scan_result, scan_meta)
    col_txt.download_button(
        label    = "📄 Download TXT Report",
        data     = text_report.encode("utf-8"),
        file_name= f"cyberfury_{filename}.txt",
        mime     = "text/plain",
        use_container_width=True,
    )

    # HTML report (with embedded thumbnail)
    try:
        data_uri   = image_to_data_uri(image)
        html_report = generate_html_report(filename, scan_result, scan_meta, data_uri)
    except Exception:
        html_report = generate_html_report(filename, scan_result, scan_meta)

    col_html.download_button(
        label    = "🌐 Download HTML Report",
        data     = html_report.encode("utf-8"),
        file_name= f"cyberfury_{filename}.html",
        mime     = "text/html",
        use_container_width=True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  Main App
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    _init_state()
    ui.apply_theme()
    _render_sidebar()
    ui.render_header()

    # ── Layout: two columns ────────────────────────────────────────────────────
    col_left, col_right = st.columns([1.35, 1], gap="large")

    # ══════════════════════════════════════════════════════════════════════════
    #  LEFT COLUMN — Upload & Controls
    # ══════════════════════════════════════════════════════════════════════════
    with col_left:
        st.markdown(
            "<h3 style='font-family:Rajdhani,sans-serif; letter-spacing:.06em;'>"
            "📥 Evidence Upload</h3>",
            unsafe_allow_html=True,
        )

        uploaded = st.file_uploader(
            label        = "",
            type         = ["jpg", "jpeg", "png", "webp"],
            help         = f"Max file size: {MAX_FILE_MB} MB",
            label_visibility = "collapsed",
        )

        # If a new file is uploaded, clear old results
        if uploaded is not None:
            if st.session_state.scan_filename != uploaded.name:
                for key in _KEYS:
                    st.session_state[key] = None
                st.session_state.scan_filename = uploaded.name

        if uploaded:
            # ── Try to open the image ──────────────────────────────────────
            try:
                # Re-open (verify() closes the file object internally)
                uploaded.seek(0)
                img = Image.open(uploaded)
                img.load()   # fully decode into memory
            except Exception as exc:
                ui.render_error(f"Cannot open image: {exc}")
                return

            st.image(img, use_container_width=True, caption=f"📎 {uploaded.name}")

            # Image info strip
            st.markdown(
                f"<p style='color:#7A8EA8; font-size:0.82rem; margin-top:-4px;'>"
                f"Dimensions: {img.width}×{img.height} px &nbsp;|&nbsp; "
                f"Mode: {img.mode} &nbsp;|&nbsp; "
                f"Format: {img.format or uploaded.name.split('.')[-1].upper()}</p>",
                unsafe_allow_html=True,
            )

            # ── Scan button ────────────────────────────────────────────────
            if st.button("🚨 RUN FORENSIC SCAN"):
                # File-size guard
                size_mb = len(uploaded.getvalue()) / (1024 * 1024)
                if size_mb > MAX_FILE_MB:
                    ui.render_error(
                        f"File is {size_mb:.1f} MB — maximum allowed is {MAX_FILE_MB} MB. "
                        "Please upload a smaller image."
                    )
                else:
                    # ── Run with live progress bar ─────────────────────────
                    with st.container():
                        model_res, meta_res = ui.run_with_progress(
                            img,
                            analyze_image,
                            analyze_metadata,
                        )

                    # Store results in session state
                    if "error" in model_res:
                        st.session_state.scan_result = None
                        ui.render_error(model_res["error"])
                    else:
                        st.session_state.scan_result = model_res
                        st.session_state.scan_meta   = meta_res
                        st.session_state.scan_image  = img
                        st.rerun()   # refresh to show results cleanly

        else:
            # No file yet — show an instructional hint
            st.markdown(
                "<p style='color:#3a5070; font-size:0.88rem; margin-top:8px;'>"
                "↑ Drag and drop or click to upload an image for analysis.</p>",
                unsafe_allow_html=True,
            )

    # ══════════════════════════════════════════════════════════════════════════
    #  RIGHT COLUMN — Results
    # ══════════════════════════════════════════════════════════════════════════
    with col_right:
        st.markdown(
            "<h3 style='font-family:Rajdhani,sans-serif; letter-spacing:.06em;'>"
            "⚖️ Analysis Report</h3>",
            unsafe_allow_html=True,
        )

        has_results  = st.session_state.scan_result is not None
        file_present = uploaded is not None

        # ── Show results only when we have them AND a file is still loaded ──
        if file_present and has_results:
            scan_result = st.session_state.scan_result
            scan_meta   = st.session_state.scan_meta
            scan_image  = st.session_state.scan_image
            filename    = st.session_state.scan_filename or "unknown"

            # ── Verdict card ──────────────────────────────────────────────
            ui.render_verdict_card(scan_result)

            # ── Explainability ────────────────────────────────────────────
            ui.render_explainability(scan_result)

            # ── Metadata ─────────────────────────────────────────────────
            if scan_meta:
                ui.render_metadata_panel(scan_meta)

            # ── Forensic tools bar ────────────────────────────────────────
            ui.render_forensic_tools(filename)

            # ── Downloadable reports ──────────────────────────────────────
            _render_downloads(filename, scan_result, scan_meta, scan_image)

            # ── Reset ─────────────────────────────────────────────────────
            ui.render_reset_button()

        elif file_present and not has_results:
            # File uploaded but scan not yet run
            ui.render_idle_placeholder()

        else:
            # No file at all
            ui.render_idle_placeholder()


if __name__ == "__main__":
    main()
