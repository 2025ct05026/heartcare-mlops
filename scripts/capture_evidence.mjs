// Screenshots come from real running services; no simulated UI is generated.
import { chromium } from 'playwright';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import assert from 'node:assert/strict';

await mkdir('screenshots', { recursive: true });
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1200, height: 850 }, deviceScaleFactor: 1 });
const browserErrors = [];
page.on('pageerror', error => browserErrors.push(String(error)));
try {
  const base = process.env.API_URL;
  assert(base);
  await page.goto(`${base}/docs`);
  const operation = page.locator('#operations-default-predict_predict_post');
  await operation.locator('.opblock-summary').click();
  await operation.getByRole('button', { name: 'Try it out' }).click();
  await operation.locator('textarea').fill(await readFile('examples/patient.json', 'utf8'));
  const reply = page.waitForResponse(r => r.url() === `${base}/predict` && r.request().method() === 'POST');
  await operation.getByRole('button', { name: 'Execute', exact: true }).click();
  const response = await reply;
  assert.equal(response.status(), 200);
  const result = await response.json();
  await operation.locator('.responses-wrapper').scrollIntoViewIfNeeded();
  await page.screenshot({ path: 'screenshots/ingress-prediction.png' });

  // Capture the native browser display of the real target API response. This
  // verifies scraping independently of Prometheus's optional JavaScript UI.
  const targetResponse = await page.goto('http://127.0.0.1:9090/api/v1/targets');
  const targetStatus = await targetResponse.json();
  assert(targetStatus.data.activeTargets.some(target => target.health === 'up'));
  await page.locator('pre').screenshot({ path: 'screenshots/prometheus.png' });

  await page.goto('http://127.0.0.1:3000/d/heartcare-service/heartcare-service-monitoring?orgId=1&from=now-10m&to=now');
  await page.getByText('Predictions since process start', { exact: true }).waitFor({ timeout: 60000 });
  await page.waitForTimeout(10000);
  await page.screenshot({ path: 'screenshots/grafana.png', fullPage: true });

  await page.goto('https://github.com/2025ct05026/heartcare-mlops/actions/runs/39261525975');
  await page.getByText('Success', { exact: true }).first().waitFor({ timeout: 30000 });
  await page.screenshot({ path: 'screenshots/github-actions.png' });
  await writeFile('evidence/browser-verification.json', JSON.stringify({
    environment: 'Disposable GitHub Actions Linux runner; cluster deleted after job',
    run_id: process.env.GITHUB_RUN_ID, ingress_url: base, ingress_response: result,
    screenshots: ['ingress-prediction.png', 'prometheus.png', 'grafana.png', 'github-actions.png']
  }, null, 2));
} catch (error) {
  await page.screenshot({ path: 'screenshots/browser-failure.png', fullPage: true });
  await writeFile('evidence/browser-failure.txt', `${page.url()}\n${error}\n${browserErrors.join('\n')}\n${await page.locator('body').innerText()}`);
  throw error;
} finally {
  await browser.close();
}
