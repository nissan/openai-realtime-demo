import { test, expect } from "@playwright/test";

test.describe("TeacherObserver", () => {
  test("teacher page renders for version-b", async ({ page }) => {
    await page.goto("/teacher?v=b&session=test-sess");
    await expect(page.getByTestId("teacher-inject-input")).toBeVisible();
  });

  test("inject input accepts text", async ({ page }) => {
    await page.goto("/teacher?v=b&session=test-sess");
    const input = page.getByTestId("teacher-inject-input");
    await input.fill("Good job, keep going!");
    await expect(input).toHaveValue("Good job, keep going!");
  });

  test("submit button is present", async ({ page }) => {
    await page.goto("/teacher?v=b&session=test-sess");
    await expect(page.getByTestId("teacher-inject-submit")).toBeVisible();
  });

  test("version-a teacher page shows info panel", async ({ page }) => {
    await page.goto("/teacher?v=a&session=test-sess");
    // Version A shows info-only (join room directly) — no inject input
    await expect(page.getByTestId("teacher-inject-input")).not.toBeVisible();
  });

  test("escalation banner has correct testid", async ({ page }) => {
    // EscalationBanner only appears after escalation — verify it's absent by default
    await page.goto("/student?v=b");
    await expect(page.getByTestId("escalation-banner")).not.toBeVisible();
  });

  test("escalation panel is absent before any escalation", async ({ page }) => {
    await page.goto("/teacher?v=b&session=test-sess");
    await expect(page.getByTestId("escalation-panel")).not.toBeVisible();
  });
});
