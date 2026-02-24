import { test, expect } from "@playwright/test";

test.describe("FlowVisualizer pipeline steps", () => {
  test("version-b visualizer is present on student page", async ({ page }) => {
    await page.goto("/student?v=b");
    await expect(page.getByTestId("flow-visualizer")).toBeVisible();
  });

  test("version-a visualizer shows STT step", async ({ page }) => {
    await page.goto("/student?v=a");
    await expect(page.getByTestId("flow-step-stt")).toBeVisible();
  });

  test("version-b visualizer does not show STT step", async ({ page }) => {
    await page.goto("/student?v=b");
    await expect(page.getByTestId("flow-step-stt")).not.toBeVisible();
  });

  test("version-b visualizer shows specialist, guardrail, tts steps", async ({ page }) => {
    await page.goto("/student?v=b");
    for (const step of ["specialist", "guardrail", "tts"]) {
      await expect(page.getByTestId(`flow-step-${step}`)).toBeVisible();
    }
  });
});
