// 冒烟测试脚本：node scripts/smoke-audit.js（依赖 /tmp/shot/node_modules 的 playwright-core）
const { chromium } = require('/tmp/shot/node_modules/playwright-core');
(async () => {
  const browser = await chromium.launch({ executablePath: '/Users/ty/Library/Caches/ms-playwright/chromium-1223/chrome-mac-x64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing' });
  const page = await browser.newPage({ viewport: { width: 1792, height: 1078 } });
  const report = {};
  let cur = 'init';
  const rec = (msg) => { (report[cur] = report[cur] || []).push(msg); };
  page.on('console', m => { if (m.type() === 'error') rec('console.error: ' + m.text().slice(0, 250)); });
  page.on('pageerror', e => rec('PAGEERROR: ' + (e.message || '').slice(0, 300)));

  cur = 'login-page';
  await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2500);
  await page.fill('input[placeholder*="账号"]', 'admin');
  await page.fill('input[placeholder*="密码"]', '123456');
  await page.click('.el-select'); await page.waitForTimeout(500);
  await page.locator('.el-select-dropdown__item').first().click();
  await page.click('button:has-text("登")');
  await page.waitForTimeout(3000);

  const routes = [
    '/satellite/satellite_network',
    '/satellite/Weixing',
    '/satellite/Xingcu',
    '/satellite/Xingneng',
    '/satellite/system_settings',
    '/satellite/Yongli',
    '/satellite/renwu/shuxing',
    '/portal',
  ];
  for (const r of routes) {
    cur = r;
    await page.goto('http://127.0.0.1:5173' + r, { waitUntil: 'networkidle' });
    await page.waitForTimeout(5000);
  }

  // 回归：连续 3 次 卫星网络 -> 系统设置 -> 卫星网络（验证 viewer destroy 无泄漏/报错）
  for (let i = 1; i <= 3; i++) {
    cur = `switch-round-${i}`;
    await page.goto('http://127.0.0.1:5173/satellite/satellite_network', { waitUntil: 'networkidle' });
    await page.waitForTimeout(4000);
    await page.goto('http://127.0.0.1:5173/satellite/system_settings', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2500);
  }
  cur = 'switch-final-network';
  await page.goto('http://127.0.0.1:5173/satellite/satellite_network', { waitUntil: 'networkidle' });
  await page.waitForTimeout(5000);
  const canvasCount = await page.locator('#cesiumContainer canvas').count();
  console.log('cesium canvas count (expect 1):', canvasCount);

  let hasError = false;
  for (const [k, v] of Object.entries(report)) {
    if (v.length) {
      hasError = true;
      console.log('=== ' + k + ' ===');
      [...new Set(v)].forEach(m => console.log('  ' + m));
    }
  }
  console.log(hasError ? '=== DONE: ERRORS FOUND ===' : '=== DONE: ZERO ERRORS ===');
  await browser.close();
})();
