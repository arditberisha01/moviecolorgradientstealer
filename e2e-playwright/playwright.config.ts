import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
    testDir: './tests',
    fullyParallel: true,
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 2 : 0,
    workers: process.env.CI ? 1 : undefined,
    reporter: 'html',
    use: {
        baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://127.0.0.1:5173',
        trace: 'on-first-retry',
    },
    webServer: process.env.PLAYWRIGHT_BASE_URL ? undefined : {
        command: 'npm run dev -- --host 127.0.0.1 --port 5173',
        cwd: '../frontend',
        url: 'http://127.0.0.1:5173',
        reuseExistingServer: true,
        timeout: 120000,
    },
    projects: [
        {
            name: 'chromium',
            use: { ...devices['Desktop Chrome'] },
        },
    ],
});
