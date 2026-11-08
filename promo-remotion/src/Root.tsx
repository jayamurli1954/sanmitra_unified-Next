import { Composition } from "remotion";
import { FPS, TOTAL_FRAMES } from "./data/script";
import { Video } from "./Video";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="OfficeMitraPromo"
        component={Video}
        durationInFrames={TOTAL_FRAMES}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{ orientation: "landscape" as const }}
      />
      <Composition
        id="OfficeMitraPromoVertical"
        component={Video}
        durationInFrames={TOTAL_FRAMES}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={{ orientation: "portrait" as const }}
      />
    </>
  );
};
