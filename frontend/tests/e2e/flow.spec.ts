import { test, expect } from "@playwright/test";

test.describe("FlowVisualizer", () => {
  test("version-a shows STT step", async ({ page }) => {
    await page.goto("/student?v=a");
    const viz = page.getByTestId("flow-visualizer");
    await expect(viz).toBeVisible();
    await expect(page.getByTestId("flow-step-stt")).toBeVisible();
  });

  test("version-b hides STT step", async ({ page }) => {
    await page.goto("/student?v=b");
    const viz = page.getByTestId("flow-visualizer");
    await expect(viz).toBeVisible();
    await expect(page.getByTestId("flow-step-stt")).not.toBeVisible();
  });

  test("version-a shows all 5 pipeline steps", async ({ page }) => {
    await page.goto("/student?v=a");
    for (const step of ["stt", "orchestrator", "specialist", "guardrail", "tts"]) {
      await expect(page.getByTestId(`flow-step-${step}`)).toBeVisible();
    }
  });

  test("version-b shows 3 pipeline steps", async ({ page }) => {
    await page.goto("/student?v=b");
    for (const step of ["specialist", "guardrail", "tts"]) {
      await expect(page.getByTestId(`flow-step-${step}`)).toBeVisible();
    }
  });
});
