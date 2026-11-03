// Record scripted flows in the Amphion front-end demo as frame sequences.
// Start the demo first (Amphion repo, dev branch): npm install && npm run dev -- --port 5180
// usage: node record.js <outDir> <light|dark> [clip ...]
// compose.py turns the frames into the animated project card.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE = 'http://localhost:5180/';
const [, , OUT, SCHEME = 'light', ...ONLY] = process.argv;

// The demo gives a recorded song one of two sample tabs, chosen by its id
// (Date.now()) being even or odd. Even ids get the G major one, so make the
// clock even: every step of the journey then shows the same tab.
const SAME_TAB = `
{ const now = Date.now; Date.now = () => { const t = now.call(Date); return t - (t % 2); }; }
`;

// Draws a soft circle wherever the "finger" taps, so viewers can follow along.
const TOUCHES = `
addEventListener('pointerdown', e => {
  const d = document.createElement('div');
  d.style.cssText = 'position:fixed;z-index:2147483647;pointer-events:none;width:46px;height:46px;border-radius:50%;' +
    'left:' + (e.clientX - 23) + 'px;top:' + (e.clientY - 23) + 'px;' + (matchMedia('(prefers-color-scheme: dark)').matches
      ? 'background:rgba(255,255,255,.22);border:2px solid rgba(255,255,255,.45);'
      : 'background:rgba(40,30,20,.20);border:2px solid rgba(40,30,20,.35);') +
    'transform:scale(.6);opacity:1;transition:transform .45s ease-out,opacity .6s ease-out';
  document.documentElement.appendChild(d);
  requestAnimationFrame(() => requestAnimationFrame(() => { d.style.transform = 'scale(1.15)'; d.style.opacity = '0'; }));
  setTimeout(() => d.remove(), 700);
}, true);
`;

const wait = ms => new Promise(r => setTimeout(r, ms));

async function tap(locator, pause = 700) {
  await locator.click({ timeout: 5000 });
  await wait(pause);
}

async function slowType(locator, text, gap = 70) {
  await locator.click();
  for (const ch of text) { await locator.press(ch === ' ' ? 'Space' : ch); await wait(gap); }
}

async function smoothScroll(app, dy, ms = 900) {
  await app.locator('html').evaluate((_, [dy, ms]) => new Promise(res => {
    const el = document.scrollingElement; const y0 = el.scrollTop; const t0 = performance.now();
    const step = t => { const k = Math.min(1, (t - t0) / ms); const e = k < .5 ? 2 * k * k : 1 - (-2 * k + 2) ** 2 / 2;
      el.scrollTop = y0 + dy * e; k < 1 ? requestAnimationFrame(step) : res(); };
    requestAnimationFrame(step);
  }), [dy, ms]);
}

// The demo is one journey with one song: record it, wait for its tab, play
// along, then practice. Each clip is one step, and each starts where the last
// one ended. setup() runs off camera; run() is recorded for exactly `len` ms.
// Keep the names and lengths in step with AMPHION_CLIPS in build_assets.py.
const btn = (app, name) => app.getByRole('button', { name, exact: false }).first();
const SONG = 'Evening Practice';
const PROCESSING = 8000; // PROCESSING_MS in the demo's MainApp.tsx

// Record a song and ask for its tab, off camera. Returns when the tab was requested.
async function makeSong(app) {
  await btn(app, 'Add Song').click();
  await btn(app, 'Record with Mic').click();
  await btn(app, 'Allow Microphone').click();
  await wait(1200);
  await btn(app, 'Stop recording').click();
  await app.getByPlaceholder('e.g., Sunday morning idea').fill(SONG);
  await btn(app, 'Make Tab').click();
  const requested = Date.now();
  await btn(app, 'Maybe later').click();
  await app.getByRole('button', { name: `More actions for ${SONG}` }).waitFor();
  return requested;
}

async function openSongWhenReady(app, requested) {
  await wait(Math.max(0, requested + PROCESSING + 600 - Date.now()));
  await app.getByRole('button', { name: `Open ${SONG} tab` }).click();
  // Let the "Your tab is ready" toast finish; the previous step already showed it.
  await app.getByText(/is ready/).first().waitFor({ state: 'hidden', timeout: 10000 }).catch(() => {});
  await wait(500);
}

const CLIPS = {
  record: {
    len: 8000,
    async setup(app) {},
    async run(app) {
      await wait(400);
      await tap(btn(app, 'Add Song'), 700);
      await tap(btn(app, 'Record with Mic'), 700);
      await tap(btn(app, 'Allow Microphone'), 1700);
      await tap(btn(app, 'Stop recording'), 600);
      await slowType(app.getByPlaceholder('e.g., Sunday morning idea'), SONG, 45);
      await wait(250);
      await tap(btn(app, 'Make Tab'), 900);
      await tap(btn(app, 'Maybe later'), 300);
    },
  },
  ready: {
    len: 6000,
    async setup(app) {
      const requested = await makeSong(app);
      // Start filming 2.5 s before the tab is ready.
      await wait(Math.max(0, requested + PROCESSING - 2500 - Date.now()));
    },
    async run(app) {
      await wait(3600); // the card turns Ready and the toast appears
      await tap(app.getByRole('button', { name: `Open ${SONG} tab` }), 300);
    },
  },
  play: {
    len: 6500,
    async setup(app) {
      await openSongWhenReady(app, await makeSong(app));
    },
    async run(app) {
      await wait(700);
      await tap(app.getByRole('button', { name: 'Play song', exact: true }).first(), 300);
    },
  },
  practice: {
    len: 7500,
    async setup(app) {
      await openSongWhenReady(app, await makeSong(app));
      await smoothScroll(app, 640, 10);
      await wait(400);
    },
    async run(app) {
      await wait(500);
      await tap(app.getByRole('button', { name: /^Speed/ }).last(), 800);
      await tap(app.getByText('75%', { exact: true }).last(), 600);
      await tap(app.getByRole('button', { name: 'Play song', exact: true }).last(), 1900);
      await tap(app.getByRole('button', { name: /loop start/i }).last(), 2300);
      await tap(app.getByRole('button', { name: /loop end/i }).last(), 300);
    },
  },
};

async function main() {
  const browser = await chromium.launch({ channel: 'chrome', args: ['--autoplay-policy=no-user-gesture-required', '--mute-audio', '--force-device-scale-factor=2'] });
  for (const [name, clip] of Object.entries(CLIPS)) {
    if (ONLY.length && !ONLY.includes(name)) continue;
    const ctx = await browser.newContext({ viewport: { width: 700, height: 1000 }, deviceScaleFactor: 2, colorScheme: SCHEME });
    await ctx.addInitScript(SAME_TAB);
    await ctx.addInitScript(TOUCHES);
    const page = await ctx.newPage();
    await page.goto(BASE);
    const app = page.frameLocator('iframe.device-screen');
    // Get past splash and sign-in, off camera.
    const signIn = app.getByRole('button', { name: 'Continue with Apple' });
    for (let i = 0; i < 10 && !(await signIn.isVisible()); i++) {
      await app.locator('main').first().click({ timeout: 5000 }).catch(() => {});
      await wait(600);
    }
    await signIn.click();
    await app.getByRole('button', { name: 'Add Song' }).waitFor();
    await wait(800);
    await clip.setup(app);
    const box = await page.locator('iframe.device-screen').boundingBox();

    const cdp = await ctx.newCDPSession(page);
    const frames = [];
    cdp.on('Page.screencastFrame', async f => {
      frames.push({ data: f.data, t: f.metadata.timestamp });
      cdp.send('Page.screencastFrameAck', { sessionId: f.sessionId }).catch(() => {});
    });
    await cdp.send('Page.startScreencast', { format: 'png', everyNthFrame: 1, maxWidth: 1400, maxHeight: 2000 });
    const start = Date.now() / 1000;
    await clip.run(app).catch(e => console.error(name, 'flow error:', e.message.split('\n').slice(0,4).join(' | ')));
    const left = clip.len - (Date.now() / 1000 - start) * 1000;
    if (left > 0) await wait(left); else console.warn(name, 'ran long by', -left, 'ms');
    const end = Date.now() / 1000;
    await cdp.send('Page.stopScreencast');

    const dir = path.join(OUT, SCHEME, name);
    fs.rmSync(dir, { recursive: true, force: true });
    fs.mkdirSync(dir, { recursive: true });
    const t0 = start;
    const list = [];
    frames.forEach((f, i) => {
      const file = `${String(i).padStart(4, '0')}.png`;
      fs.writeFileSync(path.join(dir, file), Buffer.from(f.data, 'base64'));
      list.push({ file, t: Math.max(0, f.t - t0) });
    });
    fs.writeFileSync(path.join(dir, 'frames.json'), JSON.stringify({ box, dpr: 2, length: end - t0, frames: list }));
    console.log(name, SCHEME, frames.length, 'frames', (end - t0).toFixed(1) + 's');
    await ctx.close();
  }
  await browser.close();
}
main();
