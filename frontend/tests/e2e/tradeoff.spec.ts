import { test, expect } from "@playwright/test";

test.describe("TradeoffPanel", () => {
  test("english trigger shows English tradeoff", async ({ page }) => {
    await page.goto("/student?v=a&tradeoff=english");
    const panel = page.getByTestId("tradeoff-panel");
    await expect(panel).toBeVisible();
    await expect(panel).toContainText(/english/i);
  });

  test("guardrail trigger shows guardrail tradeoff", async ({ page }) => {
    await page.goto("/student?v=a&tradeoff=guardrail");
    await expect(page.getByTestId("tradeoff-panel")).toContainText(/guardrail/i);
  });

  test("filler trigger shows filler tradeoff", async ({ page }) => {
    await page.goto("/student?v=b&tradeoff=filler");
    await expect(page.getByTestId("tradeoff-panel")).toContainText(/filler/i);
  });

  test("teacher trigger shows teacher tradeoff", async ({ page }) => {
    await page.goto("/student?v=a&tradeoff=teacher");
    await expect(page.getByTestId("tradeoff-panel")).toContainText(/teacher/i);
  });

  test("dismiss button closes the panel", async ({ page }) => {
    await page.goto("/student?v=a&tradeoff=english");
    await page.getByTestId("tradeoff-dismiss").click();
    await expect(page.getByTestId("tradeoff-panel")).not.toBeVisible();
  });
});
