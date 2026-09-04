import { mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import QRCode from "qrcode";

const downloadUrl =
  process.env.ICO_ANDROID_DOWNLOAD_URL ?? "https://incaof.com/downloads/in-case-of.apk";
const output = resolve("public/images/android-download-qr.svg");

await mkdir(dirname(output), { recursive: true });
await QRCode.toFile(output, downloadUrl, {
  type: "svg",
  errorCorrectionLevel: "M",
  margin: 2,
  width: 512,
  color: {
    dark: "#171A18",
    light: "#F6F5F0",
  },
});

console.log(`Android download QR: ${downloadUrl} -> ${output}`);
