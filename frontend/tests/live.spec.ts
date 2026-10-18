import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import type { Dossier } from "../src/types";

const dossier: Dossier = JSON.parse(readFileSync(new URL("../src/mocks/dossier.json", import.meta.url), "utf8"));

test.use({ baseURL: "http://127.0.0.1:5174" });

test.beforeEach(async ({ page }) => {
  // Only the HTTP contract is stubbed; navigation, storage and SSE parsing use
  // the real client. Browser tests never spend credits or execute a PoC.
  await page.route("http://localhost:8000/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/api/health") return route.fulfill({ json: { ok: true, service: "mimi" } });
    if (path === "/api/reports") return route.fulfill({ json: [{
      id: dossier.report_id, package_spec: dossier.package_spec,
      created_at: dossier.created_at, source: "demo", status: "complete", tier: dossier.tier,
    }] });
    if (path === `/api/reports/${dossier.report_id}/stream`) return route.fulfill({
      contentType: "text/event-stream",
      body: dossier.events.map((event) => `data: ${JSON.stringify(event)}\r\n\r\n`).join("")
        + "event: done\r\ndata: {}\r\n\r\n",
    });
    if (path === `/api/reports/${dossier.report_id}`) return route.fulfill({ json: dossier });
    return route.fulfill({ status: 404, json: { detail: "no such report" } });
  });
});

test("changing report IDs clears previous evidence when the new report fails", async ({ page }) => {
  await page.goto(`/reports/${dossier.report_id}`);
  await expect(page.getByRole("heading", { name: "Verdict", exact: true })).toBeVisible();
  await page.evaluate(() => {
    window.history.pushState({}, "", "/reports/missing-report");
    window.dispatchEvent(new PopStateEvent("popstate"));
  });
  await expect(page.getByRole("heading", { name: "Report unavailable" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Verdict", exact: true })).toHaveCount(0);
});

test("access keys persist for the tab, unlock requests, and can be cleared", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Judge access key").fill("browser-test-key");
  const unlocked = page.waitForRequest((request) =>
    request.url().endsWith("/api/reports?limit=50") && request.headers()["x-mimi-key"] === "browser-test-key",
  );
  await page.getByRole("button", { name: "Unlock inbox" }).click();
  await unlocked;
  await page.reload();
  await expect(page.getByLabel("Judge access key")).toHaveValue("browser-test-key");
  await page.getByRole("button", { name: "Clear key" }).click();
  await expect(page.getByLabel("Judge access key")).toHaveValue("");
  expect(await page.evaluate(() => sessionStorage.getItem("mimi.access_key"))).toBeNull();
});

test("a completed SSE stream stops the running indicator and exposes the final dossier", async ({ page }) => {
  await page.goto(`/reports/${dossier.report_id}`);
  await expect(page.getByRole("heading", { name: "Reply draft", exact: true })).toBeVisible();
  await expect(page.getByText("pipeline running", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Download dossier" })).toBeVisible();
});

test("research references preserve unsupported URL schemes as text", async ({ page }) => {
  const unsafe = structuredClone(dossier);
  unsafe.research.known_advisories[0].url = "javascript:void(0)";
  unsafe.research.fix_url = "data:text/plain,untrusted-reference";
  await page.route(`http://localhost:8000/api/reports/${dossier.report_id}`, (route) =>
    route.fulfill({ json: unsafe }),
  );
  await page.goto(`/reports/${dossier.report_id}`);
  await expect(page.getByText("javascript:void(0)", { exact: true })).toHaveCount(1);
  await expect(page.getByText("data:text/plain,untrusted-reference", { exact: true })).toHaveCount(1);
  await expect(page.locator('a[href^="javascript:"], a[href^="data:"]')).toHaveCount(0);
});
