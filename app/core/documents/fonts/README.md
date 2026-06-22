# Font Bundle

This directory contains bundled open-source fonts used by MandirMitra receipt rendering.

## Purpose
- Ensure deterministic PDF output across local/dev/prod.
- Avoid runtime dependence on external CDNs for critical receipt documents.
- Improve Indic-script shaping quality (Kannada/Tamil/Telugu/Malayalam/Hindi).

## Bundled fonts
- `NotoSansKannada-Regular.ttf`
- `NotoSansTamil-Regular.ttf`
- `NotoSansTelugu-Regular.ttf`
- `NotoSansMalayalam-Regular.ttf`
- `NotoSansDevanagari-Regular.ttf`

## Runtime selection policy
The backend applies strict per-language priority:
1. Bundled script-specific font (this folder)
2. Bundled generic fallback font (this folder)
3. System script-specific font
4. System generic fallback font

This policy is implemented in `app/modules/mandir_compat/router.py`.

## Notes
- Keep only required weights to control repository size.
- When adding a new script, update `_SCRIPT_FONT_FILES`, `_SCRIPT_FONT_GLOBS`, and documentation.
