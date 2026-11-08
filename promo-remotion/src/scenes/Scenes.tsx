import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { BrowserFrame } from "../components/BrowserFrame";
import { FONT, GRADIENT, theme } from "../theme";

/**
 * Seven scene visuals. Scenes tagged LIVE in script.ts are meant to be
 * REPLACED with a real screen recording — drop an <OffthreadVideo> inside the
 * <BrowserFrame> in that scene. The mock UI here is a stand-in so Studio
 * previews and renders without any assets.
 */

const line = (w: string, c = theme.line, h = 10): React.CSSProperties => ({
  width: w,
  height: h,
  borderRadius: 6,
  background: c,
  marginBottom: 10,
});

const Center: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
    {children}
  </AbsoluteFill>
);

// 0 — Hook: bills pile onto a dark background
const SceneHook: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const docs = ["BILL", "GST", "INV", "PDF"];
  return (
    <AbsoluteFill style={{ background: theme.dark }}>
      {docs.map((d, i) => {
        const s = spring({ frame, fps, delay: i * 7, config: { damping: 14 } });
        const x = ["28%", "42%", "54%", "64%"][i];
        const y = ["30%", "40%", "28%", "46%"][i];
        const rot = [-11, 6, -4, 13][i];
        return (
          <div
            key={d}
            style={{
              position: "absolute",
              left: x,
              top: y,
              width: 150,
              height: 196,
              background: "#fff",
              borderRadius: 10,
              boxShadow: "0 18px 40px rgba(0,0,0,0.45)",
              transform: `translateY(${interpolate(s, [0, 1], [-400, 0])}px) rotate(${rot}deg)`,
              opacity: s,
              padding: 18,
            }}
          >
            <div style={{ fontFamily: FONT, fontWeight: 800, color: "#94a3b8", fontSize: 18 }}>{d}</div>
            <div style={{ ...line("80%"), marginTop: 16 }} />
            <div style={line("60%")} />
            <div style={line("72%")} />
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

// 1 — CA Practice Portal
const ScenePortal: React.FC = () => (
  <Center>
    <BrowserFrame label="OfficeMitra · CA Practice Portal">
      <div style={{ display: "flex", height: "100%" }}>
        <div style={{ width: "26%", background: theme.soft, borderRight: `1px solid #eef2ff`, padding: 24 }}>
          {["#c7d2fe", theme.line, theme.line, theme.line, "#c7d2fe"].map((c, i) => (
            <div key={i} style={line(["86%", "70%", "78%", "60%", "82%"][i], c, 9)} />
          ))}
        </div>
        <div style={{ flex: 1, padding: 28 }}>
          <div style={line("40%", "#c7d2fe", 14)} />
          <div style={line("85%")} />
          <div style={line("70%")} />
          <span style={{ display: "inline-block", marginTop: 10, fontFamily: FONT, fontWeight: 800, fontSize: 15, color: theme.brand, background: "#eef2ff", padding: "5px 12px", borderRadius: 999 }}>
            Client: Acme Mfg
          </span>
        </div>
      </div>
    </BrowserFrame>
  </Center>
);

// 2 — OCR capture
const SceneOCR: React.FC = () => {
  const frame = useCurrentFrame();
  const scan = interpolate(frame, [10, 90], [0, 100], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const fields: Array<[string, string, string]> = [
    ["Vendor", "40%", "30%"],
    ["GSTIN", "40%", "50%"],
    ["Amount", "70%", "68%"],
  ];
  return (
    <Center>
      <BrowserFrame label="OCR · reading…">
        <div style={{ position: "relative", height: "100%", padding: 28 }}>
          <div style={line("50%", "#cbd5e1", 14)} />
          <div style={line("85%")} />
          <div style={line("70%")} />
          <div style={line("85%")} />
          {fields.map(([t, l, top], i) => {
            const show = scan > [34, 52, 72][i];
            return (
              <div key={t} style={{ position: "absolute", left: l, top, width: i === 2 ? "22%" : "34%", height: "13%", border: `2px solid ${theme.brand2}`, borderRadius: 6, background: "rgba(14,165,164,0.08)", opacity: show ? 1 : 0.15 }}>
                <span style={{ position: "absolute", top: -22, left: 0, fontFamily: FONT, fontSize: 15, fontWeight: 800, color: theme.brand2, background: "#fff", padding: "0 4px" }}>{t}</span>
              </div>
            );
          })}
          <div style={{ position: "absolute", left: "34%", right: "10%", top: `${18 + scan * 0.55}%`, height: 3, background: `linear-gradient(90deg,transparent,${theme.brand2},transparent)`, boxShadow: `0 0 12px ${theme.brand2}` }} />
        </div>
      </BrowserFrame>
    </Center>
  );
};

// 3 — Bill accounting (draft entry)
const SceneBill: React.FC = () => {
  const frame = useCurrentFrame();
  const rows = [
    ["48%", "#dcfce7"],
    ["56%", "#dcfce7"],
    ["38%", "#fee2e2"],
  ];
  return (
    <Center>
      <BrowserFrame label="OfficeMitra · Purchase entry">
        <div style={{ padding: 28 }}>
          <div style={line("50%", "#c7d2fe", 14)} />
          {rows.map(([w, c], i) => {
            const show = spring({ frame, fps: 30, delay: 15 + i * 12, config: { damping: 18 } });
            return (
              <div key={i} style={{ display: "flex", gap: 10, margin: "8px 0", opacity: show }}>
                <div style={{ ...line(w, theme.line), margin: 0 }} />
                <div style={{ ...line("22%", c as string), margin: 0 }} />
              </div>
            );
          })}
          <span style={{ display: "inline-block", marginTop: 12, fontFamily: FONT, fontWeight: 800, fontSize: 15, color: "#854d0e", background: "#fef9c3", padding: "5px 12px", borderRadius: 999 }}>
            Draft entry
          </span>
        </div>
      </BrowserFrame>
    </Center>
  );
};

// 4 — Confidence-routed approval
const SceneApproval: React.FC = () => {
  const frame = useCurrentFrame();
  const approve = frame > 150;
  const Row: React.FC<{ pct: string; bg: string; fg: string; action: string; abg: string; afg: string }> = ({ pct, bg, fg, action, abg, afg }) => (
    <div style={{ display: "flex", alignItems: "center", gap: 12, margin: "12px 0" }}>
      <div style={{ ...line("48%", theme.line), margin: 0 }} />
      <span style={{ fontFamily: FONT, fontWeight: 800, fontSize: 16, color: fg, background: bg, padding: "3px 12px", borderRadius: 999 }}>{pct}</span>
      <span style={{ fontFamily: FONT, fontWeight: 800, fontSize: 15, color: afg, background: abg, padding: "4px 14px", borderRadius: 999 }}>{action}</span>
    </div>
  );
  return (
    <Center>
      <BrowserFrame label="OfficeMitra · Approval queue">
        <div style={{ padding: 28 }}>
          <div style={line("50%", "#cbd5e1", 14)} />
          <div style={{ transform: approve ? "scale(1.03)" : "scale(1)", transition: "transform 0.2s" }}>
            <Row pct="97%" bg="#dcfce7" fg="#166534" action={approve ? "Approved ✓" : "Approve"} abg={approve ? "#16a34a" : theme.brand} afg="#fff" />
          </div>
          <Row pct="72%" bg="#fef9c3" fg="#854d0e" action="Review" abg={theme.line} afg={theme.sub} />
        </div>
      </BrowserFrame>
    </Center>
  );
};

// 5 — Automatic posting
const SceneAutoPost: React.FC = () => {
  const frame = useCurrentFrame();
  const stamp = spring({ frame, fps: 30, delay: 20, config: { damping: 9 } });
  return (
    <Center>
      <BrowserFrame label="OfficeMitra · General Ledger">
        <div style={{ position: "relative", height: "100%", padding: 28 }}>
          <div style={line("50%", "#c7d2fe", 14)} />
          <div style={line("85%")} />
          <div style={line("70%")} />
          <div style={line("85%")} />
          <div style={{ position: "absolute", right: "10%", top: "28%", transform: `scale(${interpolate(stamp, [0, 1], [0.3, 1])}) rotate(-8deg)`, opacity: stamp, fontFamily: FONT, fontWeight: 900, fontSize: 26, color: "#fff", background: "#16a34a", padding: "8px 18px", borderRadius: 10, boxShadow: "0 10px 24px rgba(22,163,74,0.4)" }}>
            POSTED ✓
          </div>
        </div>
      </BrowserFrame>
    </Center>
  );
};

// 6 — Payoff + CTA
const ScenePayoff: React.FC = () => {
  const frame = useCurrentFrame();
  const op = interpolate(frame, [0, 18], [0, 1], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ background: GRADIENT, alignItems: "center", justifyContent: "center", opacity: op }}>
      <div style={{ textAlign: "center", color: "#fff", fontFamily: FONT }}>
        <div style={{ fontSize: 72, fontWeight: 800, letterSpacing: -1 }}>
          OfficeMitra <span style={{ opacity: 0.75 }}>+</span> SSDV
        </div>
        <div style={{ fontSize: 26, opacity: 0.95, marginTop: 10 }}>
          AI does the first pass. You keep control.
        </div>
        <div style={{ marginTop: 26, display: "flex", gap: 10, justifyContent: "center" }}>
          {["sandbox", "tenant-isolated", "India-native"].map((t) => (
            <span key={t} style={{ fontSize: 17, fontWeight: 700, background: "rgba(255,255,255,0.18)", padding: "7px 16px", borderRadius: 999 }}>
              {t}
            </span>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const SCENE_COMPONENTS: React.FC[] = [
  SceneHook,
  ScenePortal,
  SceneOCR,
  SceneBill,
  SceneApproval,
  SceneAutoPost,
  ScenePayoff,
];
