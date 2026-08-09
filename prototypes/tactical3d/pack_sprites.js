// The yard consumes the same authored body canvas as the walkable world.
// Keep sheet geometry and naming in one place so the board, match card, and
// roster audit cannot quietly drift into different bodies again.
export const FRAME_W = 96;
export const FRAME_H = 80;
export const GROUND_ROW = 57;
export const BODY_PX = 1.10 / 32;
export const QUAD_W = FRAME_W * BODY_PX;
export const QUAD_H = FRAME_H * BODY_PX;

export const FIGHTERS = Object.freeze(["cipher", "vesper", "koa", "sable", "syn"]);
export const FACINGS = Object.freeze(["down", "up", "left", "right"]);

// Frame counts deliberately do not live here. Every loaded sheet proves its
// own count from its width, because the molded verbs do not share one length.
export const SHEETS = Object.freeze({
  idle:  { folder: "IDLE",  stem: "idle",  fps: 7,  loop: true },
  run:   { folder: "RUN",   stem: "run",   fps: 11, loop: true },
  aim:   { folder: "AIM",   stem: "aim",   fps: 6,  loop: true, stance: true },
  fire:  { folder: "FIRE",  stem: "fire",  fps: 10, loop: false },
  hurt:  { folder: "HURT",  stem: "hurt",  fps: 12, loop: false },
  death: { folder: "DEATH", stem: "death", fps: 10, loop: false, hold: true },
  kneel: { folder: "KNEEL", stem: "kneel", fps: 2,  loop: true, stance: true },
});

const BODY_NAMES = Object.freeze(["composed", "render96"]);
let configuredBody = "render96";

export function configureBody(param) {
  if (!BODY_NAMES.includes(param)) {
    throw new Error(
      `unknown body source "${param}"; the yard stages "composed" or "render96"`
    );
  }
  configuredBody = param;
}

// Pinned to the room's render96 map: a composed retune must not silently
// retune the render body.
const RENDER_FPS = Object.freeze({
  idle: 4,
  run: 11,
  aim: 2,
  fire: 10,
  hurt: 12,
  death: 10,
  kneel: 2,
});

export function fighterSlug(name) {
  const slug = name.toLowerCase().replace(/-\d+$/, "");
  if (!FIGHTERS.includes(slug)) throw new Error(`no molded fighter registered for ${name}`);
  return slug;
}

export function sheetKey(fighter, action, facing) {
  return `${fighter}:${action}:${facing}`;
}

// The serving contract, stated once where it is created: this path only
// resolves when the page is served from the REPO ROOT, which is why
// serve.cmd roots at %~dp0..\.. and all three READMEs say so. Relocating
// assets/ breaks the yard, the roster audit and the walkable room together
// — at load time, and loudly, because a missing sheet is a fault rather
// than a fallback. That is the coupling working, not the coupling failing.
export function sheetUrl(fighter, action, facing) {
  const spec = SHEETS[action];
  if (!spec) throw new Error(`no molded verb registered for ${action}`);
  // Cipher alone has the full render combat roster. The squad and SYN stay
  // composed because their render path has no combat verbs yet.
  if (configuredBody === "render96" && fighter === "cipher") {
    return `../../assets/original/cipher_render/sheets96/${spec.stem}_${facing}.png`;
  }
  return `../../assets/sprites/composed/${fighter}/${spec.folder}/${spec.stem}_${facing}.png`;
}

// Two bodies with different cadences now share verbs on one board, so fps
// belongs to (fighter, action); the room's per-verb pin was not enough here.
export function sheetFps(fighter, action) {
  const spec = SHEETS[action];
  if (!spec) throw new Error(`no molded verb registered for ${action}`);
  if (configuredBody === "render96" && fighter === "cipher") return RENDER_FPS[action];
  return spec.fps;
}

export function sheetGeometry(image, url) {
  const width = image.naturalWidth || image.width;
  const height = image.naturalHeight || image.height;
  if (height !== FRAME_H || width === 0 || width % FRAME_W !== 0) {
    throw new Error(
      `${url} is ${width}×${height}; expected a row of ${FRAME_W}×${FRAME_H} frames`
    );
  }
  return { width, height, frames: width / FRAME_W };
}

export async function loadSheetImage(fighter, action, facing) {
  const url = sheetUrl(fighter, action, facing);
  const image = new Image();
  image.decoding = "async";
  const loaded = new Promise((resolve, reject) => {
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error(`${url} did not load`));
  });
  image.src = url;
  const result = await loaded;
  sheetGeometry(result, url);
  return result;
}

// A native 48×48 crop around the body. drawImage remains 1:1: no authored
// pixel is scaled into being; callers display this canvas at integer 1×/4×.
export function idleDownThumb(image) {
  const canvas = document.createElement("canvas");
  canvas.width = 48;
  canvas.height = 48;
  const context = canvas.getContext("2d");
  context.imageSmoothingEnabled = false;
  context.drawImage(image, 24, 12, 48, 48, 0, 0, 48, 48);
  return canvas;
}
