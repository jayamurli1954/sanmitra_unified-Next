// Single source of truth for the promo: timing, captions and VO.
// Durations (seconds) match the storyboard / shot list.
export const FPS = 30;

export type Scene = {
  id: string;        // used for the per-scene VO file: public/vo/<id>.mp3
  title: string;     // on-screen caption label
  caption: string;   // lower-third caption line
  vo: string;        // voiceover for this scene (fed to edge-tts)
  seconds: number;
  kind: "LIVE" | "BUILD"; // LIVE = drop in a real screen recording here
};

export const SCENES: Scene[] = [
  {
    id: "s0_hook",
    title: "",
    caption: "Manual data entry, every single bill",
    vo: "Every bill a business receives used to mean manual data entry.",
    seconds: 4,
    kind: "BUILD",
  },
  {
    id: "s1_portal",
    title: "CA Practice Portal",
    caption: "One portal, every client",
    vo: "OfficeMitra gives the accountant one portal for every client.",
    seconds: 10,
    kind: "LIVE",
  },
  {
    id: "s2_ocr",
    title: "OCR",
    caption: "Reads vendor, GST & totals in seconds",
    vo: "Drop in a bill. OCR reads the vendor, GST and totals in seconds.",
    seconds: 12,
    kind: "BUILD",
  },
  {
    id: "s3_bill",
    title: "Bill accounting",
    caption: "A ready accounting entry — no typing",
    vo: "It becomes a ready accounting entry, no typing.",
    seconds: 12,
    kind: "LIVE",
  },
  {
    id: "s4_approval",
    title: "Confidence-routed approval",
    caption: "High-confidence = 1 click · uncertain = human review",
    vo: "High-confidence entries are one click. Anything uncertain goes to human review.",
    seconds: 12,
    kind: "LIVE",
  },
  {
    id: "s5_autopost",
    title: "Automatic posting",
    caption: "Posts straight to the books — traceable & audited",
    vo: "On approval, it posts straight to the books, traceable and audited.",
    seconds: 10,
    kind: "LIVE",
  },
  {
    id: "s6_payoff",
    title: "",
    caption: "Sandbox · never touches the live ledger",
    vo: "OfficeMitra plus SSDV. AI does the first pass. You keep control.",
    seconds: 8,
    kind: "BUILD",
  },
];

export const TOTAL_FRAMES = SCENES.reduce(
  (sum, s) => sum + Math.round(s.seconds * FPS),
  0,
);

// Flip to true AFTER running `npm run vo` to generate public/vo/<id>.mp3.
export const WITH_VO = false;
// Place a music bed at public/music.mp3 and flip to true.
export const WITH_MUSIC = false;
