import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
// H.264 at a high quality for a crisp screen-capture promo.
Config.setCodec("h264");
Config.setCrf(18);
