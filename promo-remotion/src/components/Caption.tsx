import { interpolate, useCurrentFrame } from "remotion";
import { FONT, theme } from "../theme";

export const Caption: React.FC<{
  text: string;
  durationInFrames: number;
}> = ({ text, durationInFrames }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(
    frame,
    [0, 10, durationInFrames - 12, durationInFrames],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  const y = interpolate(frame, [0, 12], [16, 0], {
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        bottom: 70,
        display: "flex",
        justifyContent: "center",
        opacity,
        transform: `translateY(${y}px)`,
      }}
    >
      <div
        style={{
          fontFamily: FONT,
          fontWeight: 800,
          fontSize: 34,
          color: "#fff",
          background: "rgba(15,23,42,0.86)",
          padding: "12px 22px",
          borderRadius: 12,
          letterSpacing: 0.2,
          boxShadow: "0 10px 30px rgba(2,6,23,0.35)",
          borderLeft: `5px solid ${theme.brand2}`,
        }}
      >
        {text}
      </div>
    </div>
  );
};
