import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { theme } from "../theme";

// A browser-chrome card. Put a real screen recording inside via <OffthreadVideo>,
// or render mock UI as children. Scales/fades in on entrance.
export const BrowserFrame: React.FC<{
  children?: React.ReactNode;
  label?: string;
}> = ({ children, label }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame, fps, config: { damping: 200 }, durationInFrames: 18 });
  const scale = interpolate(s, [0, 1], [0.94, 1]);
  const opacity = interpolate(s, [0, 1], [0, 1]);

  return (
    <div
      style={{
        width: "76%",
        aspectRatio: "16 / 9",
        background: "#fff",
        borderRadius: 16,
        boxShadow: "0 30px 70px rgba(2,6,23,0.22)",
        overflow: "hidden",
        transform: `scale(${scale})`,
        opacity,
        position: "relative",
      }}
    >
      <div
        style={{
          height: 34,
          background: "#eef2ff",
          borderBottom: `1px solid ${theme.line}`,
          display: "flex",
          alignItems: "center",
          gap: 7,
          padding: "0 14px",
        }}
      >
        {["#f87171", "#fbbf24", "#34d399"].map((c) => (
          <span
            key={c}
            style={{ width: 11, height: 11, borderRadius: 999, background: c }}
          />
        ))}
        {label ? (
          <span
            style={{
              marginLeft: 12,
              fontSize: 14,
              color: theme.muted,
              fontWeight: 700,
            }}
          >
            {label}
          </span>
        ) : null}
      </div>
      <div style={{ position: "absolute", inset: "34px 0 0 0" }}>{children}</div>
    </div>
  );
};
