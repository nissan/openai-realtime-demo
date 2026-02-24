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

  test("active step is highlighted when seeded via URL param (version-b)", async ({ page }) => {
    await page.goto("/student?v=b&activeStep=specialist");
    await expect(page.getByTestId("flow-step-specialist")).toHaveAttribute("data-active", "true");
  });

  test("inactive steps have no data-active attribute when another step is active", async ({ page }) => {
    await page.goto("/student?v=b&activeStep=specialist");
    await expect(page.getByTestId("flow-step-guardrail")).not.toHaveAttribute("data-active");
    await expect(page.getByTestId("flow-step-tts")).not.toHaveAttribute("data-active");
  });

  test("active step is highlighted for version-a (STT step)", async ({ page }) => {
    await page.goto("/student?v=a&activeStep=stt");
    await expect(page.getByTestId("flow-step-stt")).toHaveAttribute("data-active", "true");
  });
});
