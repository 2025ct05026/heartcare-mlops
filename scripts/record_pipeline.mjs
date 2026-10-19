// Record a fresh browser and the real running services. No simulated results,
// explanatory slides, narration, or audio are inserted into the recording.
import { chromium } from 'playwright';
import { spawn, execFileSync } from 'node:child_process';
import { mkdir, readFile, writeFile, open } from 'node:fs/promises';
import assert from 'node:assert/strict';

await mkdir('video', { recursive: true });
const browser = await chromium.launch({
  headless: false,
  args: ['--window-size=1366,768', '--window-position=0,0', '--no-first-run']
});
const context = await browser.newContext({ viewport: null, locale: 'en-US', timezoneId: 'UTC' });
const page = await context.newPage();
const repo = 'https://github.com/2025ct05026/heartcare-mlops';
const pause = ms => page.waitForTimeout(ms);
let pointer = { x: 650, y: 420 };
const visits = [];

async function point(x, y) {
  const chrome = await page.evaluate(() => window.outerHeight - window.innerHeight);
  const destination = { x: Math.round(x), y: Math.round(y + chrome) };
  const previous = { ...pointer };
  for (let i = 1; i <= 16; i++) {
    const fraction = i / 16;
    const eased = fraction * fraction * (3 - 2 * fraction);
    const px = Math.round(previous.x + (destination.x - previous.x) * eased);
    const py = Math.round(previous.y + (destination.y - previous.y) * eased);
    execFileSync('xdotool', ['mousemove', String(px), String(py)]);
    await pause(20);
  }
  pointer = destination;
}

async function click(locator) {
  await locator.scrollIntoViewIfNeeded();
  const box = await locator.boundingBox();
  assert(box);
  await point(box.x + box.width / 2, box.y + box.height / 2);
  await pause(300);
  await locator.click();
}

async function visit(url, wait = 5000) {
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
  visits.push({ url, time: new Date().toISOString() });
  await point(1120, 470);
  await pause(wait);
}

await page.goto(repo, { waitUntil: 'domcontentloaded' });
await pause(3000);
const log = await open('video/ffmpeg.log', 'w');
const recorder = spawn('ffmpeg', [
  '-y', '-f', 'x11grab', '-draw_mouse', '1', '-framerate', '24',
  '-video_size', '1366x768', '-i', process.env.DISPLAY,
  '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20',
  '-pix_fmt', 'yuv420p', '-an', '-movflags', '+faststart',
  'video/HeartCare_Pipeline_Demo.mp4'
], { stdio: ['pipe', 'ignore', log.fd] });
const finished = new Promise((resolve, reject) => {
  recorder.on('error', reject);
  recorder.on('close', code => code === 0 ? resolve() : reject(new Error(`Recorder exited ${code}`)));
});
let failed;
try {
  await point(585, 390);
  await pause(6000);
  await page.mouse.wheel(0, 430);
  await pause(3500);
  await visit(`${repo}/blob/main/data/clean/heart.csv`, 6000);
  await page.mouse.wheel(0, 270);
  await pause(3000);
  await visit(`${repo}/blob/main/heartcare/model.py`, 6000);
  await page.mouse.wheel(0, 410);
  await pause(4500);

  await visit('http://127.0.0.1:5000', 5000);
  const experiment = page.getByText('heartcare-cleveland', { exact: true }).first();
  await experiment.waitFor({ timeout: 45000 });
  await click(experiment);
  await pause(6500);
  const selected = page.getByText('logistic_2', { exact: true }).first();
  await selected.waitFor({ timeout: 30000 });
  await click(selected);
  await pause(7000);
  await page.mouse.wheel(0, 260);
  await pause(4000);

  await visit(`${repo}/blob/main/reports/figures/evaluation.png`, 6500);
  await visit(`${process.env.API_URL}/docs`, 3000);
  const operation = page.locator('#operations-default-predict_predict_post');
  await click(operation.locator('.opblock-summary'));
  await pause(1600);
  await click(operation.getByRole('button', { name: 'Try it out' }));
  const input = operation.locator('textarea');
  await click(input);
  await input.fill((await readFile('examples/patient.json', 'utf8')).trim());
  await pause(2800);
  const reply = page.waitForResponse(r => r.url() === `${process.env.API_URL}/predict` && r.request().method() === 'POST');
  await click(operation.getByRole('button', { name: 'Execute', exact: true }));
  const response = await reply;
  assert.equal(response.status(), 200);
  await pause(1700);
  await operation.locator('.responses-wrapper').scrollIntoViewIfNeeded();
  await point(860, 410);
  await pause(8500);

  await visit(`${repo}/actions/runs/39261525975`, 7500);
  await visit(`${repo}/blob/main/Dockerfile`, 6000);
  await visit(`${repo}/blob/main/k8s/api.yaml`, 4500);
  await page.mouse.wheel(0, 410);
  await pause(3500);
  await visit(`${repo}/actions/runs/39274915091`, 7500);

  await visit('http://127.0.0.1:3000/d/heartcare-service/heartcare-service-monitoring?orgId=1&from=now-10m&to=now&kiosk', 5000);
  await page.getByText('Predictions since process start', { exact: true }).waitFor({ timeout: 45000 });
  const patient = JSON.parse(await readFile('examples/patient.json', 'utf8'));
  for (let i = 0; i < 20; i++) {
    const invalid = i % 5 === 0;
    const reply = await fetch('http://127.0.0.1:8000/predict', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(invalid ? {} : patient)
    });
    assert.equal(reply.status, invalid ? 422 : 200);
    await pause(600);
  }
  await point(850, 530);
  await pause(7000);
  await visit('http://127.0.0.1:9090/targets', 6500);
  const body = await page.locator('body').innerText();
  if (!/heartcare/i.test(body)) {
    await visit('http://127.0.0.1:9090/api/v1/targets', 5500);
  }
  await visit(repo, 5000);
} catch (error) {
  failed = error;
  await page.screenshot({ path: 'evidence/video-browser-failure.png', fullPage: true });
  await writeFile('evidence/video-browser-failure.txt', `${page.url()}\n${error}\n${await page.locator('body').innerText()}`);
} finally {
  recorder.stdin.write('q\n');
  await finished;
  await log.close();
  await browser.close();
}
await writeFile('video/provenance.json', JSON.stringify({
  run_id: process.env.GITHUB_RUN_ID, audio: false, source: 'Real Xvfb desktop and Chromium browser capture', visits
}, null, 2));
if (failed) throw failed;
