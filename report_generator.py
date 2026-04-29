"""
report_generator.py — CyberFury AI Forensic Lab
Generates downloadable forensic reports in plain-text and HTML formats.
"""

from datetime import datetime
from typing import Optional
import io

# ─── Text Report ──────────────────────────────────────────────────────────────

_SEPARATOR   = "─" * 60
_HR          = "═" * 60


def _format_anomalies_text(anomalies: list) -> str:
    """Format anomalies for plain-text output."""
    if not anomalies:
        return "    No anomalies detected.\n"

    lines = []
    icons = {"critical": "[CRITICAL]", "warning": "[WARNING] ", "info":     "[INFO]    "}
    for a in anomalies:
        prefix = icons.get(a["severity"], "[?]      ")
        lines.append(f"    {prefix} {a['label']}")
        lines.append(f"             {a['detail']}")
        lines.append("")
    return "\n".join(lines)


def generate_text_report(
    filename: str,
    model_result: dict,
    meta_result:  dict,
) -> str:
    """
    Generate a plain-text forensic report.
    Returns the report as a string (UTF-8).
    """
    now = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")

    score    = model_result.get("ai_score",   0.0)
    real     = model_result.get("real_score", 0.0)
    verdict  = model_result.get("verdict",    "UNKNOWN")
    tier     = model_result.get("conf_label", "N/A")
    label    = model_result.get("predicted_label", "N/A")

    lines = [
        _HR,
        "    CYBERFURY — AI FORENSIC ANALYSIS REPORT",
        _HR,
        f"  Filename   : {filename}",
        f"  Analysed   : {now}",
        f"  Engine     : Organika/sdxl-detector (Hugging Face Transformers)",
        _SEPARATOR,
        "",
        "  [ VERDICT ]",
        f"  {'━'*40}",
        f"  Result             : {verdict}",
        f"  Predicted Label    : {label}",
        f"  Synthetic Prob     : {score:.2f}%",
        f"  Authentic Prob     : {real:.2f}%",
        f"  Confidence Tier    : {tier}",
        "",
    ]

    # All class scores
    all_scores = model_result.get("all_scores", {})
    if all_scores:
        lines += ["  [ CLASS PROBABILITIES ]", f"  {'━'*40}"]
        for cls, pct in all_scores.items():
            bar_len = int(pct / 5)
            bar     = "█" * bar_len + "░" * (20 - bar_len)
            lines.append(f"  {cls:<18} [{bar}] {pct:6.2f}%")
        lines.append("")

    # Explainability
    explanation = model_result.get("explanation", [])
    if explanation:
        lines += ["  [ EXPLAINABILITY ]", f"  {'━'*40}"]
        for item in explanation:
            lines.append(f"  {item['icon']} {item['heading']}")
            # word-wrap the body at ~65 chars
            body = item["body"]
            while len(body) > 65:
                cut = body[:65].rfind(" ")
                if cut == -1:
                    cut = 65
                lines.append(f"       {body[:cut]}")
                body = body[cut:].strip()
            lines.append(f"       {body}")
            lines.append("")

    # Metadata
    lines += [_SEPARATOR, "  [ METADATA ANALYSIS ]", f"  {'━'*40}"]
    lines.append(f"  Summary : {meta_result.get('summary', 'N/A')}")
    lines.append("")

    anomalies = meta_result.get("anomalies", [])
    if anomalies:
        lines.append("  Anomalies:")
        lines.append(_format_anomalies_text(anomalies))

    cam  = meta_result.get("camera_info",    {})
    soft = meta_result.get("software_info",  {})
    ts   = meta_result.get("timestamp_info", {})

    if cam:
        lines += ["  Camera Info:"]
        for k, v in cam.items():
            lines.append(f"    {k:<20}: {v}")
        lines.append("")
    if soft:
        lines += ["  Software Info:"]
        for k, v in soft.items():
            lines.append(f"    {k:<20}: {v}")
        lines.append("")
    if ts:
        lines += ["  Timestamps:"]
        for k, v in ts.items():
            lines.append(f"    {k:<20}: {v}")
        lines.append("")

    lines += [
        _HR,
        "  DISCLAIMER: This report is AI-generated and probabilistic in nature.",
        "  It should be used as supporting evidence only, not as sole proof of",
        "  authenticity or manipulation.  Always combine with expert review.",
        _HR,
        "",
    ]

    return "\n".join(lines)


# ─── HTML Report ──────────────────────────────────────────────────────────────

def generate_html_report(
    filename: str,
    model_result: dict,
    meta_result:  dict,
    image_data_uri: Optional[str] = None,
) -> str:
    """
    Generate a self-contained HTML forensic report.
    """
    now      = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    score    = model_result.get("ai_score",       0.0)
    real     = model_result.get("real_score",     0.0)
    verdict  = model_result.get("verdict",        "UNKNOWN")
    tier     = model_result.get("conf_label",     "N/A")
    label    = model_result.get("predicted_label","N/A")
    v_colour = model_result.get("verdict_colour", "#EB5757")
    tier_col = model_result.get("conf_colour",    "#F2994A")

    sev_colours = {
        "critical": "#EB5757",
        "warning":  "#F2994A",
        "info":     "#56CCF2",
    }

    # ── Sections ─────────────────────────────────────────────────────────────
    # Class probabilities
    prob_rows = ""
    for cls, pct in model_result.get("all_scores", {}).items():
        bar_col = "#EB5757" if pct == score else "#27AE60"
        prob_rows += f"""
        <tr>
            <td>{cls}</td>
            <td>
                <div style="background:#1a2a3a;height:10px;border-radius:5px;overflow:hidden;">
                    <div style="width:{pct:.1f}%;height:100%;background:{bar_col};border-radius:5px;"></div>
                </div>
            </td>
            <td style="text-align:right;font-family:monospace;">{pct:.2f}%</td>
        </tr>
        """

    # Explanations
    expl_html = ""
    for item in model_result.get("explanation", []):
        expl_html += f"""
        <div style="border-left:3px solid #2F80ED;padding:10px 14px;margin-bottom:10px;
                    background:rgba(47,128,237,0.06);border-radius:0 8px 8px 0;">
            <b style="color:#E6EDF5;font-size:.9rem;">{item['icon']} {item['heading']}</b>
            <p style="color:#7A8EA8;font-size:.83rem;margin:4px 0 0;line-height:1.55;">{item['body']}</p>
        </div>
        """

    # Anomalies
    anom_html = ""
    for a in meta_result.get("anomalies", []):
        col = sev_colours.get(a["severity"], "#7A8EA8")
        anom_html += f"""
        <div style="border:1px solid {col}40;border-radius:8px;padding:10px 14px;margin-bottom:8px;background:{col}10;">
            <b style="color:{col};font-size:.88rem;">{a['label']}</b>
            <p style="color:#7A8EA8;font-size:.82rem;margin:4px 0 0;line-height:1.5;">{a['detail']}</p>
        </div>
        """

    # Thumb
    thumb_html = ""
    if image_data_uri:
        thumb_html = f"""
        <img src="{image_data_uri}"
             style="max-width:100%;max-height:300px;object-fit:contain;
                    border-radius:10px;border:1px solid #1E3A5F;margin-bottom:16px;">
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CyberFury Report — {filename}</title>
<style>
  *{{ box-sizing:border-box; margin:0; padding:0; }}
  body{{ background:#0F1C2E; color:#E6EDF5; font-family:'Segoe UI',system-ui,sans-serif;
         font-size:14px; line-height:1.6; padding:24px; }}
  .page{{ max-width:800px; margin:0 auto; }}
  .banner{{ background:linear-gradient(135deg,#16263D,#0F1C2E); border:1px solid #1E3A5F;
             border-radius:14px; padding:24px 28px; margin-bottom:20px; position:relative; overflow:hidden; }}
  .banner::before{{ content:''; position:absolute; top:0; left:0; right:0; height:3px;
                    background:linear-gradient(90deg,#2F80ED,#56CCF2); }}
  .verdict{{ font-size:2rem; font-weight:800; letter-spacing:.06em; }}
  .badge{{ display:inline-block; padding:4px 12px; border-radius:20px;
            font-size:.78rem; font-weight:700; letter-spacing:.1em; }}
  .section{{ background:#16263D; border:1px solid #1E3A5F; border-radius:12px;
              padding:20px 22px; margin-bottom:16px; }}
  .section h3{{ color:#56CCF2; font-size:.95rem; letter-spacing:.08em;
                text-transform:uppercase; margin-bottom:14px; }}
  table{{ width:100%; border-collapse:collapse; }}
  td{{ padding:5px 8px; color:#E6EDF5; vertical-align:middle; }}
  tr:nth-child(even) td{{ background:rgba(255,255,255,0.02); }}
  .mono{{ font-family:'Courier New',monospace; font-size:.82rem; color:#56CCF2; }}
  .muted{{ color:#7A8EA8; font-size:.85rem; }}
  .meter-track{{ background:#0F1C2E; height:14px; border-radius:7px; overflow:hidden; margin:10px 0; }}
  .meter-fill{{ height:100%; border-radius:7px; }}
  footer{{ text-align:center; color:#3a5070; font-size:.78rem; margin-top:24px; }}
</style>
</head>
<body>
<div class="page">

  <!-- Header -->
  <div style="text-align:center; margin-bottom:20px;">
    <h1 style="font-size:1.8rem; letter-spacing:.12em;">🛡️ CYBERFURY</h1>
    <p class="muted" style="letter-spacing:.2em; text-transform:uppercase; font-size:.82rem;">
      AI Forensic Analysis Report
    </p>
  </div>

  <!-- Meta -->
  <div class="section" style="padding:14px 22px;">
    <table>
      <tr><td class="muted" style="width:130px;">Filename</td><td class="mono">{filename}</td></tr>
      <tr><td class="muted">Analysed</td><td class="mono">{now}</td></tr>
      <tr><td class="muted">Engine</td><td class="mono">Organika/sdxl-detector</td></tr>
    </table>
  </div>

  <!-- Thumbnail -->
  {thumb_html}

  <!-- Verdict -->
  <div class="banner">
    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
      <div>
        <p class="muted" style="font-size:.8rem; letter-spacing:.1em; text-transform:uppercase;">Verdict</p>
        <p class="verdict" style="color:{v_colour};">{verdict}</p>
        <p class="muted" style="margin-top:4px;">Label: <span class="mono">{label}</span></p>
      </div>
      <span class="badge" style="background:{tier_col}22; color:{tier_col};">{tier}</span>
    </div>

    <p class="muted" style="margin-top:14px; font-size:.8rem; letter-spacing:.08em; text-transform:uppercase;">
      Synthetic Probability
    </p>
    <div class="meter-track">
      <div class="meter-fill" style="width:{score:.1f}%; background:{v_colour};"></div>
    </div>
    <div style="display:flex; justify-content:space-between;">
      <span class="mono">AI: {score:.2f}%</span>
      <span class="mono">Real: {real:.2f}%</span>
    </div>
  </div>

  <!-- Probabilities -->
  <div class="section">
    <h3>Class Probabilities</h3>
    <table>{prob_rows}</table>
  </div>

  <!-- Explainability -->
  <div class="section">
    <h3>Explainability</h3>
    {expl_html}
  </div>

  <!-- Metadata -->
  <div class="section">
    <h3>Metadata Forensics</h3>
    <p class="muted" style="margin-bottom:14px;">{meta_result.get('summary','')}</p>
    {anom_html}
  </div>

  <footer>
    <p>⚠️ This report is AI-generated and probabilistic. Use as supporting evidence only.</p>
    <p style="margin-top:4px;">CyberFury AI Forensic Lab · {now}</p>
  </footer>

</div>
</body>
</html>"""

    return html


# ─── Convenience: encode image for HTML embedding ─────────────────────────────

def image_to_data_uri(image) -> str:
    """Convert a PIL Image to a base-64 data URI (PNG) for HTML embedding."""
    import base64
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"
