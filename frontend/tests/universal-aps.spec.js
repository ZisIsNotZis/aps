import { expect, test } from "playwright/test";

test.describe("APS Studio", () => {
  test("opens the item-function model surface and can validate and plan a sample setup", async ({ page }) => {
    await page.goto("/");

    await page.getByRole("complementary").getByRole("button", { name: "Model", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Model" })).toBeVisible();
    await expect(page.getByText("Item-flow + resource-capability kernel")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Items, inventory lots, and orders" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Items" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Resources" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Production Paths" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Equipments" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Workers" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Products" })).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Resources provide functions" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Steps consume items, occupy capability, and produce items" })).toBeVisible();
    await expect(page.locator(".if-item-card").filter({ hasText: "Finished Good" })).toBeVisible();
    await expect(page.locator(".if-resource-card").filter({ hasText: "CNC 1" })).toBeVisible();
    await expect(page.locator(".if-path-card").filter({ hasText: "make_finished" })).toBeVisible();
    await expect(page.getByRole("textbox", { name: "Item Function setup JSON" })).toBeVisible();

    await page.getByRole("button", { name: "Load Sample" }).click();
    await expect(page.getByRole("textbox", { name: "Item Function setup JSON" })).toHaveValue(/"model_kind": "item_function_v1"/);

    await Promise.all([
      page.waitForResponse((resp) => resp.url().endsWith("/api/item-function/validate") && resp.request().method() === "POST"),
      page.getByRole("button", { name: "Validate" }).click(),
    ]);
    await expect(page.locator('[aria-live="polite"]')).toContainText("Validated with 0 error(s).");
    await expect(page.getByText("No diagnostics yet, or latest validation is clean.")).toBeVisible();

    const itemFunctionBoard = page.locator(".item-function-board");
    await Promise.all([
      page.waitForResponse((resp) => resp.url().endsWith("/api/item-function/plan") && resp.request().method() === "POST"),
      itemFunctionBoard.getByRole("button", { name: "Plan from model", exact: true }).click(),
    ]);
    await expect(page.locator('[aria-live="polite"]')).toContainText("Planned with status feasible.");
    await expect(itemFunctionBoard.locator(".count-chip").filter({ hasText: "feasible" })).toBeVisible();
    await expect(itemFunctionBoard.locator(".if-row").filter({ hasText: "cut_component" }).filter({ hasText: "ORD-1" })).toBeVisible();
    await expect(itemFunctionBoard.locator(".json-preview")).toContainText('"paths_by_output_item"');
  });

  test("applies config to sidebar and allows concept CRUD", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "APS Studio" }).click();

    await expect(page.getByRole("heading", { name: "APS Studio" })).toBeVisible();
    await expect(page.getByLabel("Template")).toBeVisible();
    await page.waitForFunction(() => document.querySelectorAll(".studio-board tbody tr").length >= 4);

    await page.locator(".studio-board tbody tr").filter({ hasText: /^Discrete Manufacturing Demo/ }).first().getByRole("button", { name: "Open" }).click();
    await page.getByRole("button", { name: "Generate Data" }).click();
    await expect(page.locator('.studio-board [aria-live="polite"]')).toContainText(/Generated/);
    await expect(page.locator(".json-preview")).not.toHaveText("{}");
    expect(await page.locator(".studio-record-preview tbody tr").count()).toBeGreaterThan(0);
    await page.getByRole("button", { name: "Apply to App" }).click();

    await expect(page.getByRole("button", { name: "Tasks" })).toHaveCount(0);
    await page.getByRole("button", { name: "Resource", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Resource" })).toBeVisible();

    const beforeRows = await page.locator("tbody tr").count();
    await page.locator("label:has-text('Code') input").fill("RES-NEW");
    await page.locator("label:has-text('Name') input").fill("Utility New");
    await page.locator("label:has-text('Base price / hour') input").fill("4.2");
    await page.getByRole("button", { name: "Create" }).click();
    await page.waitForTimeout(500);
    const afterRows = await page.locator("tbody tr").count();
    expect(afterRows).toBeGreaterThan(beforeRows);
  });

  test("advanced template uses rich editors and universal planning path", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "APS Studio" }).click();

    await page.waitForFunction(() => document.querySelectorAll(".studio-board tbody tr").length >= 6);
    await page.locator(".studio-board tbody tr").filter({ hasText: "Discrete Manufacturing Advanced Demo" }).first().getByRole("button", { name: "Open" }).click();
    await page.getByRole("button", { name: "Apply to App" }).click();

    await page.getByRole("button", { name: "Order", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Order", exact: true })).toBeVisible();
    await expect(page.locator(".subbox h5").filter({ hasText: "Order lines" })).toBeVisible();

    await page.getByRole("button", { name: "Inventory", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Inventory" })).toBeVisible();
    const firstSelectCount = await page.locator("section.card select").count();
    expect(firstSelectCount).toBeGreaterThan(0);

    const [planResponse] = await Promise.all([
      page.waitForResponse((resp) => /\/api\/universal\/configs\/.+\/plan$/.test(resp.url()), { timeout: 20000 }),
      page.getByRole("button", { name: "Run Plan" }).click(),
    ]);
    expect(planResponse.status()).toBeLessThan(500);
    if (planResponse.ok()) {
      await expect(page.getByRole("heading", { name: "Run Plan" })).toBeVisible();
    } else {
      await expect(page.locator(".error")).toBeVisible();
    }
  });

  test("resource model setup shows only business resources above pinned planning surfaces", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "APS Studio" }).click();

    await page.waitForFunction(() => document.querySelectorAll(".studio-board tbody tr").length >= 6);
    await page.locator(".studio-board tbody tr").filter({ hasText: "Resource Model Discrete Manufacturing Demo" }).first().getByRole("button", { name: "Open" }).click();
    await page.getByRole("button", { name: "Apply to App" }).click();

    await expect(page.getByRole("button", { name: "Finished Good" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Component" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Machine" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Order", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Inventory", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Plan", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Operations" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Policies" })).toHaveCount(0);
    const sidebarButtons = (await page.locator(".sidebar .nav-btn").allTextContents()).map((text) => text.trim());
    expect(sidebarButtons.indexOf("Finished Good")).toBeLessThan(sidebarButtons.indexOf("Order"));
    expect(sidebarButtons.indexOf("Machine")).toBeLessThan(sidebarButtons.indexOf("Inventory"));
    expect(sidebarButtons.indexOf("Inventory")).toBeLessThan(sidebarButtons.indexOf("Plan"));

    await page.getByRole("button", { name: "Order", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Order", exact: true })).toBeVisible();
    await expect(page.locator(".subbox h5").filter({ hasText: "Requested resources" })).toBeVisible();
  });
});
