"""
metadata.py — CyberFury AI Forensic Lab
EXIF extraction, software fingerprinting, timestamp validation, and anomaly scoring.
"""

from PIL import Image
from PIL.ExifTags import TAGS
from datetime import datetime
from typing import Any

# ─── Fingerprint Databases ────────────────────────────────────────────────────

_AI_TOOLS = [
    "midjourney", "dalle", "dall-e", "stable diffusion", "automatic1111",
    "comfyui", "novelai", "invoke ai", "diffusers", "adobe firefly",
    "bing image creator", "leonardo.ai", "flux", "getimg", "nightcafe",
    "dream studio", "civitai", "seaart", "tensor.art", "ai painter",
]

_EDITING_TOOLS = [
    "adobe photoshop", "lightroom", "gimp", "affinity photo",
    "affinity designer", "capture one", "luminar", "darkroom",
    "snapseed", "vsco", "picsart", "pixelmator", "fotor",
    "canva", "befunky", "paintshop pro",
]

_CAMERA_FIELDS   = ["Make", "Model", "LensModel", "LensMake", "BodySerialNumber"]
_DATE_FIELDS     = ["DateTime", "DateTimeOriginal", "DateTimeDigitized", "GPSDateStamp"]
_EXIF_DATE_FMT   = "%Y:%m:%d %H:%M:%S"

# Severity levels (used in UI colour-coding)
SEVERITY_CRITICAL = "critical"   # strong synthetic signal
SEVERITY_WARNING  = "warning"    # possible manipulation
SEVERITY_INFO     = "info"       # neutral observation


# ─── Internal Helpers ─────────────────────────────────────────────────────────

def _safe_str(value: Any) -> str:
    """Safely convert any EXIF value to a printable string."""
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8", errors="replace").strip()
        except Exception:
            return "<binary data>"
    return str(value).strip()


def _extract_raw_exif(image: Image.Image) -> dict:
    """
    Pull raw EXIF data from a PIL Image.
    Returns an empty dict on any failure (PNG / WebP without EXIF, corrupt header, etc.)
    """
    try:
        exif_data = image._getexif()
        if not exif_data:
            return {}
        return {
            TAGS.get(tag_id, f"Tag_{tag_id}"): value
            for tag_id, value in exif_data.items()
        }
    except AttributeError:
        return {}   # format has no _getexif (PNG, WebP in some Pillow builds)
    except Exception:
        return {}


def _parse_date(date_str: str) -> datetime | None:
    """Attempt to parse an EXIF date string. Returns None on failure."""
    try:
        return datetime.strptime(date_str[:19], _EXIF_DATE_FMT)
    except Exception:
        return None


# ─── Analysis Routines ────────────────────────────────────────────────────────

def _check_software(exif: dict, anomalies: list, flags: set) -> dict:
    """Detect AI-generation or editing software from EXIF Software tag."""
    software_info = {}
    software_raw  = exif.get("Software", "")
    software_str  = _safe_str(software_raw)
    software_lc   = software_str.lower()

    if not software_str:
        return software_info

    software_info["Software"] = software_str

    # AI tool check (highest severity)
    for sig in _AI_TOOLS:
        if sig in software_lc:
            flags.add("AI_SOFTWARE_DETECTED")
            anomalies.append({
                "severity": SEVERITY_CRITICAL,
                "label":    "AI Generation Tool Detected",
                "detail":   f"Software tag contains known AI pipeline: \"{software_str}\"",
            })
            return software_info     # no need to check editing tools

    # Editing software check
    for editor in _EDITING_TOOLS:
        if editor in software_lc:
            flags.add("EDITING_SOFTWARE_DETECTED")
            anomalies.append({
                "severity": SEVERITY_WARNING,
                "label":    "Image Editing Software",
                "detail":   f"Processed with: \"{software_str}\" — original may have been altered.",
            })
            return software_info

    # Unknown software — still worth noting
    anomalies.append({
        "severity": SEVERITY_INFO,
        "label":    "Unrecognised Software",
        "detail":   f"Software tag: \"{software_str}\" — not in known AI or editing databases.",
    })
    return software_info


def _check_camera(exif: dict, anomalies: list, flags: set) -> dict:
    """Validate camera hardware metadata."""
    camera_info = {}
    for field in _CAMERA_FIELDS:
        if field in exif:
            camera_info[field] = _safe_str(exif[field])

    if not camera_info:
        flags.add("NO_CAMERA_INFO")
        anomalies.append({
            "severity": SEVERITY_WARNING,
            "label":    "No Camera Metadata",
            "detail":   (
                "Camera make, model, and lens data are absent. "
                "Legitimate photographs almost always embed this information."
            ),
        })
    return camera_info


def _check_timestamps(exif: dict, anomalies: list, flags: set) -> dict:
    """
    Extract and cross-validate all timestamps.
    Flags: mismatch between creation/modification dates, future timestamps.
    """
    timestamp_info = {}

    for field in _DATE_FIELDS:
        if field in exif:
            timestamp_info[field] = _safe_str(exif[field])

    if not timestamp_info:
        anomalies.append({
            "severity": SEVERITY_INFO,
            "label":    "No Timestamps Found",
            "detail":   "No creation or modification timestamps are embedded.",
        })
        return timestamp_info

    # Parse all parsable dates
    parsed = {
        field: _parse_date(date_str)
        for field, date_str in timestamp_info.items()
        if _parse_date(date_str) is not None
    }

    now = datetime.now()

    # Future timestamp check
    for field, dt in parsed.items():
        if dt > now:
            flags.add("FUTURE_TIMESTAMP")
            anomalies.append({
                "severity": SEVERITY_CRITICAL,
                "label":    "Future Timestamp",
                "detail":   f"{field}: {timestamp_info[field]} is dated in the future.",
            })

    # Mismatch check — compare DateTimeOriginal vs DateTime
    original = parsed.get("DateTimeOriginal")
    modified = parsed.get("DateTime")
    if original and modified and original != modified:
        delta = abs((modified - original).total_seconds())
        if delta > 86400:   # more than 24 h gap is suspicious
            flags.add("TIMESTAMP_MISMATCH")
            anomalies.append({
                "severity": SEVERITY_WARNING,
                "label":    "Timestamp Mismatch",
                "detail":   (
                    f"DateTimeOriginal ({timestamp_info['DateTimeOriginal']}) differs from "
                    f"DateTime ({timestamp_info['DateTime']}) by "
                    f"{int(delta // 3600)} h {int((delta % 3600) // 60)} m. "
                    "Possible re-export or metadata stripping."
                ),
            })

    return timestamp_info


def _check_gps(exif: dict, anomalies: list, flags: set) -> dict:
    """Check for GPS data presence (neither good nor bad — just informational)."""
    gps_info = {}
    raw_gps  = exif.get("GPSInfo")

    if raw_gps:
        flags.add("GPS_PRESENT")
        gps_info["present"] = True
        anomalies.append({
            "severity": SEVERITY_INFO,
            "label":    "GPS Coordinates Embedded",
            "detail":   "Location data is embedded. This is normal for smartphone photos.",
        })
    return gps_info


# ─── Public API ───────────────────────────────────────────────────────────────

def analyze_metadata(image: Image.Image) -> dict:
    """
    Full metadata forensic pass on a PIL Image.

    Returns
    -------
    dict with keys:
      raw           — human-readable EXIF tag → value mapping
      flags         — set of uppercase anomaly codes
      anomalies     — list[dict] of {severity, label, detail}
      camera_info   — camera hardware fields
      software_info — software tag details
      timestamp_info— parsed timestamp fields
      gps_info      — GPS presence flag
      summary       — one-line status string for the UI
      has_exif      — bool
    """
    flags     = set()
    anomalies = []

    result = {
        "raw":            {},
        "flags":          flags,
        "anomalies":      anomalies,
        "camera_info":    {},
        "software_info":  {},
        "timestamp_info": {},
        "gps_info":       {},
        "summary":        "No metadata available.",
        "has_exif":       False,
    }

    # ── Extract raw EXIF ──────────────────────────────────────────────────────
    exif = _extract_raw_exif(image)

    if not exif:
        flags.add("NO_EXIF_DATA")
        anomalies.append({
            "severity": SEVERITY_WARNING,
            "label":    "No EXIF Metadata",
            "detail":   (
                "The image contains no embedded EXIF metadata. "
                "AI-generated images and heavily post-processed images frequently lack EXIF. "
                "Screenshots and social-media re-uploads also strip metadata."
            ),
        })
        result["summary"] = "⚠️ No EXIF data found."
        return result

    result["has_exif"] = True
    result["raw"]       = {k: _safe_str(v) for k, v in exif.items()
                           if not isinstance(v, dict)}   # skip nested GPS IFD in raw

    # ── Sub-checks ────────────────────────────────────────────────────────────
    result["camera_info"]    = _check_camera(exif,     anomalies, flags)
    result["software_info"]  = _check_software(exif,   anomalies, flags)
    result["timestamp_info"] = _check_timestamps(exif, anomalies, flags)
    result["gps_info"]       = _check_gps(exif,        anomalies, flags)

    # ── Summary ───────────────────────────────────────────────────────────────
    critical_n = sum(1 for a in anomalies if a["severity"] == SEVERITY_CRITICAL)
    warning_n  = sum(1 for a in anomalies if a["severity"] == SEVERITY_WARNING)
    info_n     = sum(1 for a in anomalies if a["severity"] == SEVERITY_INFO)

    if critical_n:
        result["summary"] = f"🚨 {critical_n} critical anomal{'y' if critical_n == 1 else 'ies'} detected."
    elif warning_n:
        result["summary"] = f"⚠️ {warning_n} warning{'s' if warning_n > 1 else ''} — review recommended."
    elif info_n:
        result["summary"] = f"ℹ️ Metadata present, {info_n} informational note{'s' if info_n > 1 else ''}."
    else:
        result["summary"] = "✅ Metadata appears clean and consistent."

    return result
