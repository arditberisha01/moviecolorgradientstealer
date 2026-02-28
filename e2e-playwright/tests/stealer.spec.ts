import { test, expect } from '@playwright/test'

test.describe('Color Stealer 2.0', () => {
  test('loads homepage and key tabs', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('h1')).toContainText('Color Stealer')
    await expect(page.getByRole('button', { name: /Upload File/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /Paste URL/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /Movie Search/i })).toBeVisible()
  })

  test('upload flow updates UI when a video is selected', async ({ page }) => {
    await page.goto('/')

    const fileInput = page.locator('input[type="file"]')
    await fileInput.setInputFiles({
      name: 'test-video.mp4',
      mimeType: 'video/mp4',
      buffer: Buffer.from('fake video payload'),
    })

    await expect(page.getByRole('button', { name: /Change File/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /Waiting for video|Steal Grade from Frame/i })).toBeVisible()
  })

  test('url button is disabled until URL is valid', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('button', { name: /Paste URL/i }).click()

    await page.getByPlaceholder(/Paste YouTube or Vimeo link/i).fill('not-a-url')
    const analyzeBtn = page.getByRole('button', { name: /Steal Grade from Current Time/i })
    await expect(analyzeBtn).toBeDisabled()

    await page.getByPlaceholder(/Paste YouTube or Vimeo link/i).fill('https://example.com/video')
    await expect(analyzeBtn).toBeEnabled()
  })
})
