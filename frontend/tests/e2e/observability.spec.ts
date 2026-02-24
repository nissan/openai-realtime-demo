import { test, expect } from "@playwright/test";

test.describe("Frontend observability — /events proxy", () => {
  test("page load emits page.loaded event to /events", async ({ page }) => {
    let captured: unknown;
    await page.route("**/events", async route => {
      captured = JSON.parse(route.request().postData() ?? "{}");
      await route.fulfill({
        body: JSON.stringify({ ok: true }),
        contentType: "application/json",
      });
    });
    await page.goto("/student?v=b");
    await expect.poll(() => captured).toMatchObject({
      event_name: "page.loaded",
      attributes: { version: "b" },
    });
  });

  test("question selection emits question.selected event to /events", async ({ page }) => {
    const events: unknown[] = [];
    await page.route("**/events", async route => {
      events.push(JSON.parse(route.request().postData() ?? "{}"));
      await route.fulfill({
        body: JSON.stringify({ ok: true }),
        contentType: "application/json",
      });
    });
    await page.goto("/student?v=b");
    await page.getByTestId("suggested-question").first().click();
    await expect
      .poll(() => events.some((e: any) => e.event_name === "question.selected"))
      .toBeTruthy();
  });
});
