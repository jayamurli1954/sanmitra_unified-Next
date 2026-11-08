import {
  AbsoluteFill,
  Audio,
  Series,
  staticFile,
} from "remotion";
import { Caption } from "./components/Caption";
import { FPS, SCENES, WITH_MUSIC, WITH_VO } from "./data/script";
import { SCENE_COMPONENTS } from "./scenes/Scenes";
import { theme } from "./theme";

export const Video: React.FC<{ orientation?: "landscape" | "portrait" }> = ({
  orientation = "landscape",
}) => {
  const portrait = orientation === "portrait";
  return (
    <AbsoluteFill style={{ background: theme.soft }}>
      {WITH_MUSIC ? (
        <Audio src={staticFile("music.mp3")} volume={0.18} />
      ) : null}

      <Series>
        {SCENES.map((scene, i) => {
          const dur = Math.round(scene.seconds * FPS);
          const SceneComp = SCENE_COMPONENTS[i];
          return (
            <Series.Sequence key={scene.id} durationInFrames={dur}>
              <AbsoluteFill
                style={{
                  // On the vertical cut, lift the frame up so the caption sits
                  // in the lower third rather than dead-centre.
                  justifyContent: portrait ? "flex-start" : "center",
                  paddingTop: portrait ? "22%" : 0,
                }}
              >
                <SceneComp />
              </AbsoluteFill>

              {scene.caption ? (
                <Caption text={scene.caption} durationInFrames={dur} />
              ) : null}

              {WITH_VO ? (
                <Audio src={staticFile(`vo/${scene.id}.mp3`)} />
              ) : null}
            </Series.Sequence>
          );
        })}
      </Series>
    </AbsoluteFill>
  );
};
