import fs from "node:fs/promises";
import path from "node:path";
import sharp from "sharp";

const sourceRoot = path.resolve(process.cwd(), "../assets");
const outputRoot = path.resolve(process.cwd(), "public/assets");
await fs.mkdir(outputRoot, { recursive: true });

await sharp(path.join(sourceRoot, "persona-roster-v2.png"))
  .resize(1536, 512, { fit: "cover" })
  .webp({ quality: 92, smartSubsample: true })
  .toFile(path.join(outputRoot, "persona-roster-v2.webp"));

const runnerSource = path.join(sourceRoot, "money-runner-source-v1.png");
const { data, info } = await sharp(runnerSource)
  .ensureAlpha()
  .raw()
  .toBuffer({ resolveWithObject: true });

const pixelCount = info.width * info.height;
const background = new Uint8Array(pixelCount);
const queue = new Int32Array(pixelCount);
let head = 0;
let tail = 0;

function isChroma(pixel) {
  const offset = pixel * info.channels;
  const red = data[offset];
  const green = data[offset + 1];
  const blue = data[offset + 2];
  return (
    green > 55 &&
    green - Math.max(red, blue) > 12 &&
    green > red * 1.08 &&
    green > blue * 1.12
  );
}

function seed(pixel) {
  if (background[pixel] || !isChroma(pixel)) return;
  background[pixel] = 1;
  queue[tail++] = pixel;
}

for (let x = 0; x < info.width; x += 1) {
  seed(x);
  seed((info.height - 1) * info.width + x);
}
for (let y = 0; y < info.height; y += 1) {
  seed(y * info.width);
  seed(y * info.width + info.width - 1);
}

while (head < tail) {
  const pixel = queue[head++];
  const x = pixel % info.width;
  const y = Math.floor(pixel / info.width);
  if (x > 0) seed(pixel - 1);
  if (x + 1 < info.width) seed(pixel + 1);
  if (y > 0) seed(pixel - info.width);
  if (y + 1 < info.height) seed(pixel + info.width);
}

for (let pixel = 0; pixel < pixelCount; pixel += 1) {
  const offset = pixel * info.channels;
  if (background[pixel]) {
    data[offset + 3] = 0;
    continue;
  }

  const red = data[offset];
  const green = data[offset + 1];
  const blue = data[offset + 2];
  const dominance = green - Math.max(red, blue);

  // Remove strongly saturated chroma pixels even when they are enclosed by
  // the character silhouette (for example, the pocket behind the money bag).
  if (green > 150 && dominance > 75) {
    data[offset + 3] = 0;
    continue;
  }

  const x = pixel % info.width;
  const y = Math.floor(pixel / info.width);
  const touchesBackground =
    (x > 0 && background[pixel - 1]) ||
    (x + 1 < info.width && background[pixel + 1]) ||
    (y > 0 && background[pixel - info.width]) ||
    (y + 1 < info.height && background[pixel + info.width]);
  if (!touchesBackground) continue;

  if (dominance <= 5) continue;
  const keep = Math.max(0, Math.min(1, 1 - (dominance - 5) / 42));
  data[offset + 3] = Math.min(data[offset + 3], Math.round(255 * keep));
  data[offset + 1] = Math.min(green, Math.max(red, blue));
}

await sharp(data, {
  raw: {
    width: info.width,
    height: info.height,
    channels: info.channels,
  },
})
  .trim({ background: { r: 0, g: 0, b: 0, alpha: 0 }, threshold: 8 })
  .resize(512, 512, {
    fit: "contain",
    background: { r: 0, g: 0, b: 0, alpha: 0 },
  })
  .png({ compressionLevel: 9, palette: false })
  .toFile(path.join(outputRoot, "money-runner-v1.png"));

console.log(
  JSON.stringify({
    status: "passed",
    roster: "public/assets/persona-roster-v2.webp",
    runner: "public/assets/money-runner-v1.png",
  }),
);
