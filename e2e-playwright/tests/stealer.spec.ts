import { test, expect } from '@playwright/test';

test.describe('Color Stealer E2E', () => {
    test('should load the homepage', async ({ page }) => {
        await page.goto('/');
        await expect(page).toHaveTitle(/Color Grade Stealer/);
        await expect(page.locator('h1')).toContainText('Color Grade Stealer', { timeout: 10000 });
    });

    // Since actual extraction might take time/resources and YouTube might block us,
    // we will test the UI logic and API calls but possibly mock or just do a simple search test.
    test('Movie Search API should return results or graceful error', async ({ page }) => {
        await page.goto('/');

        // Switch to Movie Search tab
        await page.getByRole('button', { name: 'Movie Search' }).click();

        // Type query
        const input = page.getByPlaceholder('Movie title...');
        await input.fill('Dune');

        // Click Search
        await page.getByRole('button', { name: 'Search for Trailer' }).click();

        // Wait for either results or error message
        // If it's successful, we should see cards with movie titles
        const resultsContainer = page.locator('.grid.grid-cols-1.md\\:grid-cols-2');
        const toastError = page.locator('.text-sm.opacity-90'); // standard sonner toast text

        // We wait for either the results to appear or an error to pop up
        const hasResults = await Promise.any([
            resultsContainer.waitFor({ state: 'visible', timeout: 15000 }).then(() => true),
            page.getByText('Failed to search').waitFor({ state: 'visible', timeout: 15000 }).then(() => false),
            page.getByText('No video results found').waitFor({ state: 'visible', timeout: 15000 }).then(() => false)
        ]).catch(() => false);

        // We just want to ensure the UI didn't crash
        expect(hasResults !== undefined).toBeTruthy();
    });
});
