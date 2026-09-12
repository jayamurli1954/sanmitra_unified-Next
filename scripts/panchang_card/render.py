"""Render MandirMitra Panchang HTML card to PNG via Playwright Chromium."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from scripts.panchang_card.card_data import PACKAGE_DIR, build_card_context

EXPORT_SIZES = (
    ("whatsapp", 1080, 1350),
    ("instagram", 1080, 1350),
    ("facebook", 1200, 1500),
)


def render_html(context: dict[str, Any]) -> str:
    env = Environment(
        loader=FileSystemLoader(str(PACKAGE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    return env.get_template("template.html").render(**context)


def write_rendered_html(context: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_html(context), encoding="utf-8")
    return path


def screenshot_card(
    html_path: Path,
    output_path: Path,
    *,
    width: int = 1080,
    height: int = 1350,
    device_scale_factor: float = 2,
) -> Path:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Playwright is required. Install with: "
            ".venv\\Scripts\\python.exe -m pip install playwright && "
            ".venv\\Scripts\\python.exe -m playwright install chromium"
        ) from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    uri = html_path.resolve().as_uri()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(
                viewport={"width": width, "height": height},
                device_scale_factor=device_scale_factor,
            )
            page.goto(uri, wait_until="networkidle")
            page.wait_for_timeout(200)
            card = page.locator("#panchang-card")
            card.screenshot(path=str(output_path), type="png")
        finally:
            browser.close()
    return output_path


def export_card_pngs(
    data: dict[str, Any],
    output_dir: Path,
    *,
    prefix: str | None = None,
    keep_html: bool = False,
) -> dict[str, Path]:
    context = build_card_context(data)
    date_iso = context.get("date_iso") or datetime.now().strftime("%Y_%m_%d")
    stem = prefix or f"panchang_{date_iso}"
    output_dir.mkdir(parents=True, exist_ok=True)

    html_path = output_dir / f"{stem}.html"
    write_rendered_html(context, html_path)

    # Cache day JSON for reruns / debugging
    (output_dir / f"{stem}.json").write_text(
        json.dumps(context, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    outputs: dict[str, Path] = {}
    # Capture master at WhatsApp size, then resize variants with Pillow if available.
    master = output_dir / f"{stem}_whatsapp_1080x1350.png"
    screenshot_card(html_path, master, width=1080, height=1350)
    outputs["whatsapp"] = master
    outputs["instagram"] = master

    facebook = output_dir / f"{stem}_facebook_1200x1500.png"
    try:
        from PIL import Image

        Image.open(master).convert("RGB").resize((1200, 1500), Image.Resampling.LANCZOS).save(
            facebook, format="PNG", optimize=True
        )
        outputs["facebook"] = facebook
    except Exception:
        screenshot_card(html_path, facebook, width=1200, height=1500)
        outputs["facebook"] = facebook

    if not keep_html:
        # Keep JSON; HTML is large with file:// font URIs — drop unless requested.
        html_path.unlink(missing_ok=True)

    return outputs
