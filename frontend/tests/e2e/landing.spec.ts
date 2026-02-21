import { test, expect } from "@playwright/test";

test.describe("Landing page", () => {
  test("shows version selector with two cards", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("Version A — LiveKit")).toBeVisible();
    await expect(page.getByText("Version B — OpenAI Realtime Direct")).toBeVisible();
  });

  test("version A start demo navigates to ?v=a", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "Start Demo →" }).first().click();
    await expect(page).toHaveURL(/\?v=a/);
  });

  test("version B start demo navigates to ?v=b", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "Start Demo →" }).last().click();
    await expect(page).toHaveURL(/\?v=b/);
  });

  test("architecture comparison table toggles", async ({ page }) => {
    await page.goto("/");
    await page.getByText("Architecture Comparison").click();
    await expect(page.getByText("LiveKit JWT → audio/video room")).toBeVisible();
  });
});

test.describe("Student page", () => {
  test("version a shows LiveKit UI", async ({ page }) => {
    await page.goto("/student?v=a");
    await expect(page.getByText("Version A — LiveKit")).toBeVisible();
  });

  test("version b shows OpenAI Realtime UI", async ({ page }) => {
    await page.goto("/student?v=b");
    await expect(page.getByText("Version B — OpenAI Realtime")).toBeVisible();
  });

  test("suggested questions are shown", async ({ page }) => {
    await page.goto("/student?v=a");
    await expect(page.getByText("What is 25% of 80?")).toBeVisible();
    await expect(page.getByText("Why did World War I start?")).toBeVisible();
  });
});
