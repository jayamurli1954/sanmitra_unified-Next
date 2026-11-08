"""Generate per-scene voiceover MP3s with edge-tts (free, offline-capable TTS).

Usage:
    pip install edge-tts
    python scripts/generate_vo.py
    # then set WITH_VO = true in src/data/script.ts

Writes public/vo/<scene-id>.mp3 for each scene, reading the VO text straight
from src/data/script.ts so the audio never drifts from the on-screen timing.
"""
from __future__ import annotations

import asyncio
import re
from pathlib import Path

VOICE = "en-IN-PrabhatNeural"  # or en-IN-NeerjaNeural (female)
RATE = "+5%"

ROOT = Path(__file__).resolve().parent.parent
SCRIPT_TS = ROOT / "src" / "data" / "script.ts"
OUT_DIR = ROOT / "public" / "vo"


def parse_scenes(ts: str) -> list[tuple[str, str]]:
    """Extract (id, vo) pairs from the SCENES array in script.ts."""
    pairs: list[tuple[str, str]] = []
    # Each scene object has an `id:` and a `vo:` string literal.
    for block in re.split(r"\{\s*", ts):
        m_id = re.search(r'id:\s*"([^"]+)"', block)
        m_vo = re.search(r'vo:\s*"((?:[^"\\]|\\.)*)"', block)
        if m_id and m_vo:
            vo = m_vo.group(1).encode().decode("unicode_escape")
            pairs.append((m_id.group(1), vo))
    return pairs


async def synth(text: str, out_path: Path) -> None:
    import edge_tts

    communicate = edge_tts.Communicate(text, VOICE, rate=RATE)
    await communicate.save(str(out_path))


async def main() -> None:
    scenes = parse_scenes(SCRIPT_TS.read_text(encoding="utf-8"))
    if not scenes:
        raise SystemExit("No scenes parsed from script.ts")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for scene_id, vo in scenes:
        out = OUT_DIR / f"{scene_id}.mp3"
        print(f"  {scene_id:14s} -> {out.name}  \"{vo[:48]}...\"")
        await synth(vo, out)
    print(f"\nDone. {len(scenes)} clips in {OUT_DIR}")
    print("Now set WITH_VO = true in src/data/script.ts")


if __name__ == "__main__":
    asyncio.run(main())
