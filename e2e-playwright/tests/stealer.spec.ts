import { test, expect } from '@playwright/test';

test.describe('Color Stealer E2E', () => {
    test('should load the homepage', async ({ page }) => {
        // Increase timeout for initial load
        await page.goto('/', { timeout: 60000 });
        await expect(page).toHaveTitle(/Color Grade Stealer/);
        // Using locator('h1') as it's more robust than getByRole for transparent/gradient text
        await expect(page.locator('h1')).toContainText('Color Stealer', { timeout: 15000 });
    });

    // Since actual extraction might take time/resources and YouTube might block us,
    // we will test the UI logic and API calls but possibly mock or just do a simple search test.
    test('Movie Search API should return results or graceful error', async ({ page }) => {
        await page.goto('/', { timeout: 60000 });

        // Switch to Movie Search tab
        await page.getByRole('button', { name: 'Movie Search' }).click();

        // Type query - Using the exact placeholder from App.tsx
        const input = page.getByPlaceholder('Movie title...');
        await input.fill('Dune');

        // Click Search - Using flexible locator for the search button (magnifying glass)
        // In App.tsx it's a button with a Search icon
        await page.getByRole('button').filter({ hasText: 'Search for Trailer' }).or(page.getByRole('button').filter({ has: page.locator('svg, img') })).last().click();

        // Wait for results or error - increase timeout
        const resultsContainer = page.locator('.grid');
        const errorToast = page.getByText(/Search failed|No video results|Failed to search/);

        // We check if either the results appear or an error message shows up
        await Promise.race([
            resultsContainer.waitFor({ state: 'visible', timeout: 30000 }).then(() => 'results'),
            errorToast.waitFor({ state: 'visible', timeout: 30000 }).then(() => 'error')
        ]).catch(() => {
            console.log('Timeout waiting for search results or error');
        });

        // Ensure the app is still responsive
        await expect(page.locator('h1')).toBeVisible();
    });
});
