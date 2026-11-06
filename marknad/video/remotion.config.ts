import { Config } from "@remotion/cli/config";

// Skarpt UI: hög jpeg-kvalitet per ruta, låg CRF, yuv420p så Instagram tar filen.
Config.setVideoImageFormat("jpeg");
Config.setJpegQuality(100);
Config.setCodec("h264");
Config.setCrf(16);
Config.setPixelFormat("yuv420p");
Config.setOverwriteOutput(true);
