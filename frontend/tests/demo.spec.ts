import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import type { Dossier } from "../src/types";

const dossier: Dossier = JSON.parse(readFileSync(new URL("../src/mocks/dossier.json", import.meta.url), "utf8"));

test("production replay opens by keyboard, exports evidence, and makes no API calls", async ({ page }) => {
  const errors: string[] = [];
  const apiRequests: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("request", (request) => {
    if (request.url().includes("/api/")) apiRequests.push(request.url());
  });
  await page.goto("/");
  expect((await (await page.request.get("/demo-manifest.json")).json()).fixture_report_id).toBe(dossier.report_id);
  await expect(page.getByRole("status")).toContainText("Fixed sample data only");
  await expect(page.getByLabel("Judge access key")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Run triage" })).toHaveCount(0);
  const open = page.getByRole("link", { name: "Open sample dossier" });
  await open.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("heading", { name: dossier.report_id, exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Verdict", exact: true })).toBeVisible();
  await expect(page.getByText("pipeline running", { exact: true })).toHaveCount(0);
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download dossier" }).click();
  const download = await downloadPromise;
  const stream = await download.createReadStream();
  const chunks: Buffer[] = [];
  for await (const chunk of stream!) chunks.push(chunk);
  expect(JSON.parse(Buffer.concat(chunks).toString())).toEqual(dossier);
  await page.reload();
  await expect(page.getByRole("heading", { name: dossier.report_id, exact: true })).toBeVisible();
  expect(apiRequests).toEqual([]);
  expect(errors).toEqual([]);
});

test("unknown replay report IDs show an error rather than another report's evidence", async ({ page }) => {
  await page.goto("/#/reports/does-not-exist");
  await expect(page.getByRole("heading", { name: "Report unavailable" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Verdict", exact: true })).toHaveCount(0);
  await page.getByRole("link", { name: "inbox", exact: true }).first().click();
  await expect(page.getByRole("link", { name: "Open sample dossier" })).toBeVisible();
});

test("the replay remains usable on a phone without page overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByRole("link", { name: "Open sample dossier" }).click();
  await expect(page.getByRole("heading", { name: "Verdict", exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.getByRole("heading", { name: "Reply draft", exact: true }).scrollIntoViewIfNeeded();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
