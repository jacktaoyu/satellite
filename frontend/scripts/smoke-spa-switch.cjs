// SPA 内部路由切换回归：不刷新页面，点击侧边菜单反复进出卫星网络页
const { chromium } = require('/tmp/shot/node_modules/playwright-core');
(async () => {
  const browser = await chromium.launch({ executablePath: '/Users/ty/Library/Caches/ms-playwright/chromium-1223/chrome-mac-x64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing' });
  const page = await browser.newPage({ viewport: { width: 1792, height: 1078 } });
  const errs = [];
  page.on('console', m => { if (m.type() === 'error') errs.push('console.error: ' + m.text().slice(0, 200)); });
  page.on('pageerror', e => errs.push('PAGEERROR: ' + (e.message || '').slice(0, 300)));

  await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  await page.fill('input[placeholder*="账号"]', 'admin');
  await page.fill('input[placeholder*="密码"]', '123456');
  await page.click('.el-select'); await page.waitForTimeout(500);
  await page.locator('.el-select-dropdown__item').first().click();
  await page.click('button:has-text("登")');
  await page.waitForTimeout(3000);

  for (let i = 1; i <= 3; i++) {
    await page.click('.el-menu-item:has-text("系统设置")');
    await page.waitForTimeout(2500);
    await page.click('.el-menu-item:has-text("卫星网络")');
    await page.waitForTimeout(4000);
    const n = await page.locator('#cesiumContainer .cesium-widget').count();
    console.log(`round ${i}: cesium widget count = ${n}`);
  }
  console.log(errs.length ? 'ERRORS:\n' + [...new Set(errs)].join('\n') : 'SPA SWITCH: ZERO ERRORS');
  await browser.close();
})();
