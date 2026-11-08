# OfficeMitra + SSDV — Promo video (Remotion)

A standalone [Remotion](https://remotion.dev) project that renders the
"one bill's journey" promo: **CA Practice Portal → OCR → Bill accounting →
Approval → Automatic posting → Payoff**.

Timing, captions and voiceover all come from one file: [`src/data/script.ts`](src/data/script.ts).

## Quick start

```bash
cd promo-remotion
npm install
npm run studio          # opens Remotion Studio to preview/scrub
```

Render:

```bash
npm run render          # 1920x1080 landscape -> out/officemitra_promo_landscape.mp4
npm run render:vertical # 1080x1920 vertical  -> out/officemitra_promo_vertical.mp4
```

## Add the voiceover (edge-tts, free)

```bash
pip install edge-tts
npm run vo              # writes public/vo/<scene-id>.mp3 from the VO in script.ts
```

Then set `WITH_VO = true` in [`src/data/script.ts`](src/data/script.ts) and re-render.
For music, drop a bed at `public/music.mp3` and set `WITH_MUSIC = true`.

## Drop in real screen recordings (recommended)

Scenes tagged **LIVE** in `script.ts` (Portal, Bill accounting, Approval, Auto-post)
ship with mock UI as a stand-in. Replace each with a real capture:

1. Record the screen at 1920×1080, save to `public/recordings/<name>.mp4`.
2. In [`src/scenes/Scenes.tsx`](src/scenes/Scenes.tsx), inside that scene's
   `<BrowserFrame>`, swap the mock markup for:

   ```tsx
   import { OffthreadVideo, staticFile } from "remotion";
   // ...
   <OffthreadVideo src={staticFile("recordings/portal.mp4")} />
   ```

Trim spinners before importing; keep each clip to the scene's duration.

## Structure

```
src/
  Root.tsx            two compositions (landscape + vertical)
  Video.tsx           master timeline (Series of scenes + captions + audio)
  data/script.ts      scenes: id, caption, VO, seconds  <-- edit here
  theme.ts            brand tokens / gradient
  components/         Caption, BrowserFrame
  scenes/Scenes.tsx   the 7 scene visuals (replace LIVE ones with recordings)
scripts/generate_vo.py  edge-tts VO generator
public/                 vo/*.mp3, music.mp3, recordings/*.mp4
```

Total runtime ≈ 68s @ 30fps. Edit a scene's `seconds` in `script.ts` and the
timeline, captions and VO all follow automatically.
