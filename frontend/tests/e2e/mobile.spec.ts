import { test, expect } from "@playwright/test";

/**
 * Mobile viewport smoke tests.
 * Runs on Pixel 5 (mobile-chrome) and iPhone 13 (mobile-safari).
 * 4 tests × 2 mobile browsers = 8 total.
 */
test.describe("Mobile layout smoke tests", () => {
  test("landing page renders on mobile", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Voice AI Tutor" })).toBeVisible();
    await expect(page.getByText("Version A — LiveKit")).toBeVisible();
    await expect(page.getByText("Version B — OpenAI Realtime Direct")).toBeVisible();
  });

  test("student page version-a loads on mobile", async ({ page }) => {
    await page.goto("/student?v=a");
    await expect(page.getByTestId("flow-visualizer")).toBeVisible();
  });

  test("student page version-b loads on mobile", async ({ page }) => {
    await page.goto("/student?v=b");
    await expect(page.getByTestId("flow-visualizer")).toBeVisible();
  });

  test("suggested questions panel visible on mobile", async ({ page }) => {
    await page.goto("/student?v=b");
    await expect(page.getByText("Try asking...")).toBeVisible();
  });
});
