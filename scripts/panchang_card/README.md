# Panchang HTML card pack
#
# Generate:
#   .venv\Scripts\python.exe scripts\generate_panchang_card.py --date 2026-08-27
#
# Output:
#   tmp/panchang_card/panchang_YYYY_MM_DD_whatsapp_1080x1350.png
#   tmp/panchang_card/panchang_YYYY_MM_DD_facebook_1200x1500.png
#
# Fonts: reused from app/core/documents/fonts (Noto Kannada + Devanagari)
# Frame: artwork/frame.svg — gold border, parchment, corner flourishes (static SVG layer)
# Logos: prefer logos/*.png (cropped from brand reference); SVG placeholders remain as fallback
# Artwork: artwork/diya.png, artwork/moon.png (optional decorative crops)
#
# Stack: JSON → Jinja2 → HTML+CSS+SVG frame → Playwright → PNG
#
# Requires (dev):
#   pip install -r requirements-dev.txt
#   python -m playwright install chromium
