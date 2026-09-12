"""Panchang social-media infographic renderer (Pillow + HarfBuzz via libraqm).

Uses a fixed PNG template and overlays EN / Kannada / Hindi text from Panchang JSON.
Source translations mirror frontend/src/utils/panchangWhatsAppMessage.js.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

try:
    from PIL import Image, ImageDraw, ImageFont, features as pil_features
except ImportError as exc:  # pragma: no cover - environment guard
    raise RuntimeError("Pillow is required for panchang infographic rendering") from exc

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parents[1]
DEFAULT_I18N = PACKAGE_DIR / "panchang_i18n.json"
DEFAULT_LAYOUT = PACKAGE_DIR / "layout_branded.json"
DEFAULT_TEMPLATE = PACKAGE_DIR / "template_branded.png"
LEGACY_LAYOUT = PACKAGE_DIR / "layout_default.json"
LEGACY_TEMPLATE = PACKAGE_DIR / "template_default.png"
REFERENCE_DESIGN = PACKAGE_DIR / "assets" / "reference_design.jpg"

FONT_DIRS = (
    REPO_ROOT / "app" / "core" / "documents" / "fonts",
    REPO_ROOT / "app" / "modules" / "mandir_compat" / "data" / "fonts",
    Path(r"C:\Windows\Fonts"),
    Path("/usr/share/fonts/truetype/noto"),
    Path("/usr/share/fonts/opentype/noto"),
)

LATIN_FONT_CANDIDATES = (
    "NotoSans-Regular.ttf",
    "arial.ttf",
    "Arial.ttf",
    "LiberationSans-Regular.ttf",
    "DejaVuSans.ttf",
)

SCRIPT_FONT_CANDIDATES = {
    "kannada": ("NotoSansKannada-Regular.ttf", "Tunga.ttf", "Nirmala.ttc"),
    "hindi": ("NotoSansDevanagari-Regular.ttf", "Mangal.ttf", "Nirmala.ttc"),
    "latin": LATIN_FONT_CANDIDATES,
}


@dataclass(frozen=True)
class TriText:
    en: str
    kn: str
    hi: str


@dataclass(frozen=True)
class ExportSize:
    name: str
    width: int
    height: int


EXPORT_SIZES = (
    ExportSize("whatsapp", 1080, 1350),
    ExportSize("instagram", 1080, 1350),
    ExportSize("facebook", 1200, 1500),
)


def require_raqm() -> None:
    if pil_features is not None and not pil_features.check("raqm"):
        raise RuntimeError(
            "Pillow was built without RAQM/HarfBuzz shaping; Kannada/Hindi text will break. "
            "Install libraqm and rebuild Pillow, or use the project .venv."
        )


def _find_font(candidates: tuple[str, ...]) -> Path:
    for directory in FONT_DIRS:
        if not directory.is_dir():
            continue
        for filename in candidates:
            path = directory / filename
            if path.is_file():
                return path
    raise FileNotFoundError(f"No font found among: {', '.join(candidates)}")


def load_fonts(layout: dict[str, Any]) -> dict[str, Any]:
    sizes = layout.get("fonts", {})
    fonts: dict[str, Any] = {}
    for key, size in sizes.items():
        if key.endswith("_kn") or "kn" in key:
            path = _find_font(SCRIPT_FONT_CANDIDATES["kannada"])
        elif key.endswith("_hi") or "hi" in key:
            path = _find_font(SCRIPT_FONT_CANDIDATES["hindi"])
        else:
            path = _find_font(SCRIPT_FONT_CANDIDATES["latin"])
        fonts[key] = ImageFont.truetype(str(path), int(size))
    fonts["table_kn"] = fonts.get("table_kn") or ImageFont.truetype(
        str(_find_font(SCRIPT_FONT_CANDIDATES["kannada"])), int(sizes.get("table_kn", 24))
    )
    fonts["table_hi"] = fonts.get("table_hi") or ImageFont.truetype(
        str(_find_font(SCRIPT_FONT_CANDIDATES["hindi"])), int(sizes.get("table_hi", 24))
    )
    fonts["table_en"] = fonts.get("table_en") or ImageFont.truetype(
        str(_find_font(SCRIPT_FONT_CANDIDATES["latin"])), int(sizes.get("table_en", 26))
    )
    return fonts


def load_i18n(path: Path | None = None) -> dict[str, dict[str, dict[str, str]]]:
    payload = json.loads((path or DEFAULT_I18N).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("panchang_i18n.json must be a JSON object")
    return payload


def load_layout(path: Path | None = None) -> dict[str, Any]:
    payload = json.loads((path or DEFAULT_LAYOUT).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("layout JSON must be a JSON object")
    return payload


def _lookup(table: str, key: str, i18n: dict[str, dict[str, dict[str, str]]]) -> TriText:
    cleaned = (key or "").strip()
    if not cleaned:
        return TriText("—", "—", "—")
    hit = i18n.get(table, {}).get(cleaned)
    if hit:
        return TriText(cleaned, hit.get("kn") or cleaned, hit.get("hi") or cleaned)
    return TriText(cleaned, cleaned, cleaned)


def _split_tokens(value: str) -> list[str]:
    return [part for part in re.split(r"\s+", (value or "").strip()) if part]


def _translate_masa(value: str, i18n: dict[str, dict[str, dict[str, str]]]) -> TriText:
    tokens = _split_tokens(value)
    if not tokens:
        return TriText("—", "—", "—")
    if len(tokens) == 1:
        return _lookup("masa", tokens[0], i18n)
    prefix = tokens[0]
    month = tokens[-1]
    month_tri = _lookup("masa", month, i18n)
    if prefix.lower() == "adhika":
        return TriText(
            value,
            f"ಅಧಿಕ {month_tri.kn}",
            f"अधिक {month_tri.hi}",
        )
    return TriText(value, value, value)


def _translate_tithi(name: str, paksha: str, i18n: dict[str, dict[str, dict[str, str]]]) -> TriText:
    tithi = _lookup("tithi", name, i18n)
    if not paksha:
        return tithi
    pak = _lookup("paksha", paksha, i18n)
    return TriText(
        f"{paksha} {name}".strip(),
        f"{pak.kn} {tithi.kn}".strip(),
        f"{pak.hi} {tithi.hi}".strip(),
    )


def _samvatsara_name(data: dict[str, Any]) -> str:
    hindu = data.get("date", {}).get("hindu", {}) or {}
    samvatsara = data.get("samvatsara") or hindu.get("samvatsara") or {}
    for candidate in (
        hindu.get("samvatsara_name"),
        samvatsara.get("name") if isinstance(samvatsara, dict) else None,
    ):
        if candidate:
            return str(candidate).strip()
    shaka = str(hindu.get("samvat_shaka") or "")
    parts = shaka.split()
    return parts[-1] if parts else ""


def format_clock(value: Any) -> str:
    if not value or value == "N/A":
        return "—"
    text = str(value)
    if "AM" in text or "PM" in text:
        return text
    if re.fullmatch(r"\d{1,2}:\d{2}(:\d{2})?", text):
        hour_str, minute = text.split(":")[:2]
        hour = int(hour_str)
        period = "PM" if hour >= 12 else "AM"
        display = 12 if hour == 0 else hour - 12 if hour > 12 else hour
        return f"{display}:{minute} {period}"
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.strftime("%I:%M %p").lstrip("0")
    except ValueError:
        return text


def time_range(block: Any) -> str:
    if not block:
        return "—"
    if isinstance(block, list):
        parts = [time_range(item) for item in block]
        joined = ", ".join(part for part in parts if part and part != "—")
        return joined or "—"
    if not isinstance(block, dict):
        return "—"
    start = format_clock(block.get("start") or block.get("start_time") or block.get("start_datetime"))
    end = format_clock(block.get("end") or block.get("end_time") or block.get("end_datetime"))
    if start != "—" and end != "—":
        return f"{start} – {end}"
    return start if start != "—" else end


def build_text_payload(
    data: dict[str, Any],
    i18n: dict[str, dict[str, dict[str, str]]] | None = None,
) -> dict[str, str]:
    i18n = i18n or load_i18n()
    gregorian = data.get("date", {}).get("gregorian", {}) or {}
    hindu = data.get("date", {}).get("hindu", {}) or {}
    location = data.get("location", {}) or {}
    panchang = data.get("panchang", {}) or {}
    tithi = panchang.get("tithi", {}) or {}
    nakshatra = panchang.get("nakshatra", {}) or {}
    yoga = panchang.get("yoga", {}) or {}
    karana = panchang.get("karana", {}) or {}
    vara = panchang.get("vara", {}) or {}
    kaala = data.get("inauspicious_times") or data.get("kaala") or {}
    good = data.get("auspicious_times") or data.get("muhurat") or {}
    extra_bad = data.get("additional_inauspicious_times") or {}

    ayana_name = data.get("ayana") if isinstance(data.get("ayana"), str) else (data.get("ayana") or {}).get("name", "")
    vara_name = vara.get("name") or gregorian.get("day") or gregorian.get("day_of_week") or ""
    karana_name = karana.get("current") or karana.get("name") or ""

    samvatsara = _lookup("samvatsara", _samvatsara_name(data), i18n)
    ayana = _lookup("ayana", str(ayana_name), i18n)
    masa = _translate_masa(str(hindu.get("month") or ""), i18n)
    vara_tri = _lookup("vara", str(vara_name), i18n)
    if vara.get("sanskrit"):
        vara_tri = TriText(vara_tri.en, vara_tri.kn, str(vara["sanskrit"]))
    tithi_tri = _translate_tithi(str(tithi.get("name") or ""), str(tithi.get("paksha") or hindu.get("paksha") or ""), i18n)
    nakshatra_tri = _lookup("nakshatra", str(nakshatra.get("name") or ""), i18n)
    yoga_tri = _lookup("yoga", str(yoga.get("name") or ""), i18n)
    karana_tri = _lookup("karana", str(karana_name), i18n)

    date_label = gregorian.get("formatted") or gregorian.get("date") or "Today"
    city = location.get("city") or "Temple"

    vishesha_lines: list[str] = []
    seen_vishesha: set[str] = set()
    for item in data.get("south_india_special") or []:
        if not isinstance(item, dict):
            continue
        line = ""
        if item.get("text"):
            line = str(item["text"])
        elif item.get("english"):
            kn = item.get("kannada") or ""
            hi = item.get("sanskrit") or ""
            line = f"{item['english']} | {kn} | {hi}".strip(" |")
        key = line.lower()
        if line and key not in seen_vishesha:
            seen_vishesha.add(key)
            vishesha_lines.append(line)
    # Infographic: avoid duplicating festival lines already in south_india_special.
    # Do not append special_notes.summary (repeats festival + moon note).

    def muhurta_line(label: str, value: str) -> str:
        return f"{label}: {value}" if value and value != "—" else ""

    payload = {
        "title_en": "🙏 Today's Panchang",
        "title_kn": "ಇಂದಿನ ಪಂಚಾಂಗ",
        "location_date": f"{city} · {date_label}",
        "samvatsara_en": samvatsara.en,
        "samvatsara_kn": samvatsara.kn,
        "samvatsara_hi": samvatsara.hi,
        "ayana_en": ayana.en,
        "ayana_kn": ayana.kn,
        "ayana_hi": ayana.hi,
        "masa_en": masa.en,
        "masa_kn": masa.kn,
        "masa_hi": masa.hi,
        "vara_en": vara_tri.en,
        "vara_kn": vara_tri.kn,
        "vara_hi": vara_tri.hi,
        "tithi_en": tithi_tri.en,
        "tithi_kn": tithi_tri.kn,
        "tithi_hi": tithi_tri.hi,
        "nakshatra_en": nakshatra_tri.en,
        "nakshatra_kn": nakshatra_tri.kn,
        "nakshatra_hi": nakshatra_tri.hi,
        "yoga_en": yoga_tri.en,
        "yoga_kn": yoga_tri.kn,
        "yoga_hi": yoga_tri.hi,
        "karana_en": karana_tri.en,
        "karana_kn": karana_tri.kn,
        "karana_hi": karana_tri.hi,
        "label_samvatsara": "Samvatsara",
        "label_ayana": "Ayana",
        "label_masa": "Masa",
        "label_vara": "Vara",
        "label_tithi": "Tithi",
        "label_nakshatra": "Nakshatra",
        "label_yoga": "Yoga",
        "label_karana": "Karana",
        "inauspicious_title": "Inauspicious",
        "auspicious_title": "Auspicious",
        "vishesha_title": "Vara Vishesha",
        "rahu_kala": muhurta_line("Rahu Kala", time_range(kaala.get("rahu_kaal") or kaala.get("rahu"))),
        "yamaganda": muhurta_line("Yamaganda", time_range(kaala.get("yamaganda"))),
        "gulika_kala": muhurta_line("Gulika Kala", time_range(kaala.get("gulika"))),
        "dur_muhurta": muhurta_line("Dur Muhurta", time_range(extra_bad.get("dur_muhurta"))),
        "varjyam": muhurta_line("Varjyam", time_range(extra_bad.get("varjyam"))),
        "abhijit": muhurta_line("Abhijit", time_range(good.get("abhijit_muhurat") or good.get("abhijit"))),
        "brahma_muhurat": muhurta_line("Brahma Muhurat", time_range(good.get("brahma_muhurat") or good.get("brahma"))),
        "amrita_kalam": muhurta_line("Amrita Kalam", time_range(good.get("amrita_kalam") or kaala.get("amrita"))),
        "footer_brand": "Generated by MandirMitra · SanMitra Tech",
        "footer_disclaimer": "For guidance only — confirm with temple tradition before muhurta use.",
    }
    for idx in range(1, 4):
        payload[f"vishesha_{idx}"] = ""
    for idx, line in enumerate(vishesha_lines[:3], start=1):
        payload[f"vishesha_{idx}"] = f"• {line}" if not line.startswith("•") else line
    return payload


def _script_runs(text: str) -> list[tuple[str, str]]:
    runs: list[tuple[str, str]] = []
    current: list[str] = []
    current_script = "latin"
    for char in text:
        code = ord(char)
        if 0x0C80 <= code <= 0x0CFF:
            script = "kannada"
        elif 0x0900 <= code <= 0x097F:
            script = "hindi"
        else:
            script = "latin"
        if current and script != current_script:
            runs.append(("".join(current), current_script))
            current = []
        current_script = script
        current.append(char)
    if current:
        runs.append(("".join(current), current_script))
    return runs


def _draw_mixed_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    fonts: dict[str, Any],
    *,
    fill: str,
    anchor: str = "la",
) -> None:
    x, y = xy
    if anchor == "ma":
        total = sum(_text_width(draw, run, _font_for_script(script, fonts)) for run, script in _script_runs(text))
        x -= total // 2
    elif anchor == "ra":
        total = sum(_text_width(draw, run, _font_for_script(script, fonts)) for run, script in _script_runs(text))
        x -= total
    for run, script in _script_runs(text):
        font = _font_for_script(script, fonts)
        draw.text((x, y), run, font=font, fill=fill, anchor="la")
        x += _text_width(draw, run, font)


def _font_for_script(script: str, fonts: dict[str, Any]) -> Any:
    if script == "kannada":
        return fonts["table_kn"]
    if script == "hindi":
        return fonts["table_hi"]
    return fonts["table_en"]


def _font_for_field(field_name: str, fonts: dict[str, Any], field_spec: dict[str, Any]) -> Any:
    font_key = field_spec.get("font") or "table_en"
    if font_key in fonts:
        return fonts[font_key]
    if field_name.endswith("_kn"):
        return fonts["table_kn"]
    if field_name.endswith("_hi"):
        return fonts["table_hi"]
    return fonts["table_en"]


def _text_width(draw: ImageDraw.ImageDraw, text: str, font: Any) -> int:
    if not text:
        return 0
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0]


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: Any, max_width: int) -> list[str]:
    if not text:
        return []
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if _text_width(draw, candidate, font) <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _draw_text_pad(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: Any,
    *,
    fill: str,
    anchor: str,
    pad_fill: str,
    pad_x: int = 8,
    pad_y: int = 3,
) -> None:
    box = draw.textbbox(xy, text, font=font, anchor=anchor)
    draw.rectangle(
        (box[0] - pad_x, box[1] - pad_y, box[2] + pad_x, box[3] + pad_y),
        fill=pad_fill,
    )
    draw.text(xy, text, font=font, fill=fill, anchor=anchor)


def _draw_field(
    draw: ImageDraw.ImageDraw,
    field_name: str,
    text: str,
    spec: dict[str, Any],
    fonts: dict[str, Any],
    colors: dict[str, str],
) -> None:
    if not text:
        return
    font = _font_for_field(field_name, fonts, spec)
    color_key = spec.get("color", "text")
    fill = colors.get(color_key, colors.get("text", "#1B3A1B"))
    x, y = spec["xy"]
    anchor = spec.get("anchor", "la")
    max_width = int(spec.get("max_width", 0))

    if field_name.startswith("vishesha_") and field_name != "vishesha_title":
        _draw_mixed_text(draw, (x, y), text, fonts, fill=fill, anchor=anchor)
        return

    lines = [text]
    if max_width > 0 and _text_width(draw, text, font) > max_width:
        lines = _wrap_text(draw, text, font, max_width)

    pad_key = spec.get("pad")
    pad_fill = colors.get(pad_key) if pad_key else None
    line_height = font.size + 6
    for line_idx, line in enumerate(lines):
        yy = y + line_idx * line_height
        if pad_fill:
            _draw_text_pad(draw, (x, yy), line, font, fill=fill, anchor=anchor, pad_fill=pad_fill)
        else:
            draw.text((x, yy), line, font=font, fill=fill, anchor=anchor)


def _resolve_fill(image: Image.Image, region: dict[str, Any]) -> str | tuple[int, ...]:
    if "fill_sample" in region:
        sx, sy = region["fill_sample"]
        return image.getpixel((int(sx), int(sy)))
    return region.get("fill", "#F3EBDD")


def _apply_blank_regions(image: Image.Image, layout: dict[str, Any]) -> Image.Image:
    """Paint over baked-in reference text so overlays do not double-print."""
    draw = ImageDraw.Draw(image)
    for region in layout.get("blank_regions", []):
        x1, y1, x2, y2 = region["xyxy"]
        draw.rectangle((x1, y1, x2, y2), fill=_resolve_fill(image, region))
    if layout.get("template_source"):
        header_bg = image.getpixel((540, 100))
        draw.rectangle((235, 58, 845, 175), fill=header_bg)
    return image


def _load_base_image(layout: dict[str, Any], template_path: Path | None) -> Image.Image:
    canvas = layout.get("canvas", {})
    width = int(canvas.get("width", 1080))
    height = int(canvas.get("height", 1350))
    source_rel = layout.get("template_source")
    if source_rel:
        source = PACKAGE_DIR / str(source_rel)
        if not source.is_file():
            source = REFERENCE_DESIGN
        if source.is_file():
            image = Image.open(source).convert("RGBA").resize((width, height), Image.Resampling.LANCZOS)
            return _apply_blank_regions(image, layout)
    template = template_path or DEFAULT_TEMPLATE
    if not template.is_file():
        create_default_template(template, layout)
    image = Image.open(template).convert("RGBA")
    return _apply_blank_regions(image, layout) if layout.get("blank_regions") else image


def render_infographic(
    data: dict[str, Any],
    *,
    template_path: Path | None = None,
    layout_path: Path | None = None,
    i18n_path: Path | None = None,
) -> Image.Image:
    require_raqm()
    layout = load_layout(layout_path)
    fonts = load_fonts(layout)
    colors = layout.get("colors", {})
    text_payload = build_text_payload(data, load_i18n(i18n_path))

    image = _load_base_image(layout, template_path)
    draw = ImageDraw.Draw(image)

    for field_name, spec in layout.get("fields", {}).items():
        _draw_field(draw, field_name, text_payload.get(field_name, ""), spec, fonts, colors)
    return image


def create_branded_template(path: Path, layout: dict[str, Any] | None = None) -> Path:
    """Build template from reference artwork; logos/decor stay, dynamic text areas are cleared."""
    layout = layout or load_layout()
    canvas = layout.get("canvas", {})
    width = int(canvas.get("width", 1080))
    height = int(canvas.get("height", 1350))
    source = PACKAGE_DIR / str(layout.get("template_source", "assets/reference_design.jpg"))
    if not source.is_file():
        source = REFERENCE_DESIGN
    if source.is_file():
        image = Image.open(source).convert("RGB").resize((width, height), Image.Resampling.LANCZOS)
    else:
        image = Image.new("RGB", (width, height), "#F3EBDD")
    image = _apply_blank_regions(image, layout)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG")
    return path


def create_default_template(path: Path, layout: dict[str, Any] | None = None, *, plain: bool = False) -> Path:
    """Plain fallback template, or branded when reference artwork is available."""
    if not plain and (REFERENCE_DESIGN.is_file() or (layout or load_layout()).get("template_source")):
        return create_branded_template(path, layout)
    layout = layout or load_layout()
    canvas = layout.get("canvas", {})
    width = int(canvas.get("width", 1080))
    height = int(canvas.get("height", 1350))
    image = Image.new("RGB", (width, height), "#F7F2E8")
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle((40, 40, width - 40, height - 40), radius=24, outline="#C8A951", width=3)
    draw.rounded_rectangle((60, 190, width - 60, 700), radius=16, fill="#FFFFFF", outline="#C8E6C9", width=2)
    draw.rounded_rectangle((60, 720, 520, 980), radius=16, fill="#FFF5F5", outline="#FFCDD2", width=2)
    draw.rounded_rectangle((560, 720, width - 60, 980), radius=16, fill="#F1F8E9", outline="#C8E6C9", width=2)
    draw.rounded_rectangle((60, 990, width - 60, 1180), radius=16, fill="#FFFFFF", outline="#E0E0E0", width=2)
    draw.rectangle((0, height - 90, width, height), fill="#1B5E20")

    labels = [
        (130, 230, "Samvatsara"),
        (130, 288, "Ayana"),
        (130, 346, "Masa"),
        (130, 404, "Vara"),
        (130, 462, "Tithi"),
        (130, 520, "Nakshatra"),
        (130, 578, "Yoga"),
        (130, 636, "Karana"),
    ]
    latin = ImageFont.truetype(str(_find_font(SCRIPT_FONT_CANDIDATES["latin"])), 22)
    for x, y, label in labels:
        draw.text((x, y), label, font=latin, fill="#1B5E20", anchor="la")

    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG")
    return path


def export_infographic(
    data: dict[str, Any],
    output_dir: Path,
    *,
    template_path: Path | None = None,
    layout_path: Path | None = None,
    i18n_path: Path | None = None,
    prefix: str = "panchang",
) -> dict[str, Path]:
    base = render_infographic(
        data,
        template_path=template_path,
        layout_path=layout_path,
        i18n_path=i18n_path,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, Path] = {}
    for spec in EXPORT_SIZES:
        if spec.width == base.width and spec.height == base.height:
            rendered = base
        else:
            rendered = base.resize((spec.width, spec.height), Image.Resampling.LANCZOS)
        out_path = output_dir / f"{prefix}_{spec.name}_{spec.width}x{spec.height}.png"
        rendered.save(out_path, format="PNG", optimize=True)
        outputs[spec.name] = out_path
    return outputs


def render_infographic_bytes(data: dict[str, Any], **kwargs: Any) -> bytes:
    image = render_infographic(data, **kwargs)
    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
