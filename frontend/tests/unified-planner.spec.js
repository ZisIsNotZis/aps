import { expect, test } from "playwright/test";

test.describe("Unified Planner", () => {
  test("loads scenarios, loads a model, and runs a plan", async ({ page }) => {
    await page.goto("/");

    // The UnifiedPlanner is rendered directly on the home page
    await expect(page.getByRole("heading", { name: "Unified APS Planner" })).toBeVisible();

    // Should see scenario cards
    await expect(page.getByText("Discrete Manufacturing")).toBeVisible();
    await expect(page.getByText("One machine, one rule, one order")).toBeVisible();

    // The discrete manufacturing scenario should be selected by default
    const scenarioCard = page.locator(".scenario-card.selected");
    await expect(scenarioCard).toContainText("Discrete Manufacturing");

    // Load the scenario
    await page.getByRole("button", { name: "Load Scenario" }).click();
    await expect(page.getByRole("heading", { name: "Planning Model" })).toBeVisible();

    // Verify model stats are shown in the chips
    await expect(page.getByText(/entities/)).toBeVisible();
    await expect(page.getByText(/rules/)).toBeVisible();
    await expect(page.getByText(/orders/)).toBeVisible();

    // Should see entity, rule, and order details (all sections open by default)
    await expect(page.getByText("steel_kg").first()).toBeVisible();
    await expect(page.getByText("cnc_machine").first()).toBeVisible();
    await expect(page.getByText("make_component").first()).toBeVisible();
    await expect(page.getByText("ORD-1").first()).toBeVisible();

    // Run the plan — use the button inside the unified planner section
    await page.locator(".unified-planner").getByRole("button", { name: "Run Plan" }).click();
    await expect(page.getByRole("heading", { name: "Plan Results" })).toBeVisible();

    // Verify result stats
    await expect(page.getByText("Status").first()).toBeVisible();
    await expect(page.getByText("Makespan").first()).toBeVisible();

    // Should show order outcomes
    await expect(page.getByText("Order Outcomes")).toBeVisible();
    await expect(page.getByText("ORD-1")).toBeVisible();

    // Should show scheduled blocks
    await expect(page.getByText("Scheduled Blocks")).toBeVisible();
    await expect(page.getByRole("cell", { name: "make_component" })).toBeVisible();

    // Should show Gantt chart
    await expect(page.getByText("Gantt Chart")).toBeVisible();
    await expect(page.getByText("1 blocks")).toBeVisible();

    // Navigate back to model
    await page.locator(".unified-planner").getByRole("button", { name: "Back to Model" }).click();
    await expect(page.getByRole("heading", { name: "Planning Model" })).toBeVisible();

    // Navigate back to scenarios
    await page.locator(".unified-planner").getByRole("button", { name: "Scenarios" }).click();
    await expect(page.getByText("Select Scenario")).toBeVisible();
  });

  test("shows error when backend is unavailable", async ({ page }) => {
    // Intercept and reject the scenarios fetch
    await page.route("**/api/unified/scenarios", (route) => route.abort("connectionrefused"));
    await page.goto("/");
    await expect(page.getByText(/Failed to load scenarios/)).toBeVisible();
  });
});
