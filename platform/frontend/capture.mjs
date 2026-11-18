import { chromium } from 'playwright';
import fs from 'fs';

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  const dir = './screenshots';
  if (!fs.existsSync(dir)){
      fs.mkdirSync(dir);
  }

  // Set viewport to desktop to verify navbar horizontal row
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
  
  await page.screenshot({ path: 'screenshots/navbar_verification_1440.png' });
  
  console.log("Screenshot saved at screenshots/navbar_verification_1440.png");
  await browser.close();
})();
