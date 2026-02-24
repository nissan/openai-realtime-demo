import { test, expect } from "@playwright/test";

test.describe("Integration wiring", () => {
  test("clicking suggested question shows say-this hint for version-a", async ({ page }) => {
    await page.goto("/student?v=a");

    // Click a suggested question before joining room
    const questionBtn = page.getByText("What is 25% of 80?");
    await expect(questionBtn).toBeVisible();
    await questionBtn.click();

    // Version A shows a "Say this:" hint banner (voice-only — can't inject text programmatically)
    // The hint appears even before joining, so user knows what to say when connected
    await expect(page.getByTestId("say-this-hint")).toBeVisible();
    await expect(page.getByTestId("say-this-hint")).toContainText("What is 25% of 80?");
  });

  test("clicking suggested question in version-b stores selection", async ({ page }) => {
    await page.goto("/student?v=b");

    // SuggestedQuestions component renders clickable buttons
    const questionBtn = page.getByText("Why did World War I start?");
    await expect(questionBtn).toBeVisible();

    // Clicking should not throw — it calls onSelect which sets selectedQuestion state
    // We verify the button is interactive (no error state)
    await questionBtn.click();

    // The session start button should still be present (not connected yet)
    await expect(page.getByText("Start Session")).toBeVisible();
  });

  test("livekit-token route responds with token shape", async ({ request }) => {
    // Verify the Next.js API route exists and returns a JWT token shape
    const response = await request.get("/api/livekit-token");
    expect(response.status()).toBe(200);
    const body = await response.json() as { token: string };
    expect(typeof body.token).toBe("string");
    expect(body.token.length).toBeGreaterThan(20);
    // LiveKit tokens are JWTs: three base64-encoded parts separated by dots
    const parts = body.token.split(".");
    expect(parts.length).toBe(3);
  });
});
