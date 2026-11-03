// Render an SVG to a transparent PNG with Chrome.
// usage: node rasterize.js <in.svg> <out.png> <scale>
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const [, , input, output, scale = '2'] = process.argv;
  const src = fs.readFileSync(input, 'utf8');
  const [, w, h] = src.match(/width="([\d.]+)" height="([\d.]+)"/);
  const browser = await chromium.launch({ channel: 'chrome' });
  const page = await browser.newPage({
    viewport: { width: Math.ceil(+w), height: Math.ceil(+h) },
    deviceScaleFactor: +scale,
  });
  await page.goto('file://' + path.resolve(input));
  await page.screenshot({ path: output, omitBackground: true });
  await browser.close();
})();
