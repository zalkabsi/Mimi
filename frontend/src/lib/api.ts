/**
 * Typed client for the Mimi backend (backend/mimi/api.py).
 *
 * Base URL is a single constant: VITE_API_BASE if set, else the local
 * FastAPI dev server. VITE_USE_MOCK=1 swaps every call for the fixture in
 * src/mocks/dossier.json so the UI can be developed without a backend.
 */

import type {
  Dossier,
  ReportListItem,
  ReportSubmission,
  StageEvent,
  SubmitResponse,
} from "../types";
import mockDossierJson from "../mocks/dossier.json";

export const API_BASE: string =
  (import.meta.env.VITE_API_BASE as string | undefined) ??
  "http://localhost:8000";

export const USE_MOCK: boolean = import.meta.env.VITE_USE_MOCK === "1";

const mockDossier = mockDossierJson as unknown as Dossier;
const ACCESS_KEY_STORAGE_KEY = "mimi.access_key";
let inMemoryAccessKey: string | null | undefined;

export function getStoredAccessKey(): string {
  if (inMemoryAccessKey !== undefined) return inMemoryAccessKey ?? "";
  try {
    return window.sessionStorage.getItem(ACCESS_KEY_STORAGE_KEY) ?? "";
  } catch {
    return "";
  }
}

export function storeAccessKey(accessKey: string | null): void {
  const value = accessKey?.trim() || null;
  inMemoryAccessKey = value;
  try {
    if (value) window.sessionStorage.setItem(ACCESS_KEY_STORAGE_KEY, value);
    else window.sessionStorage.removeItem(ACCESS_KEY_STORAGE_KEY);
  } catch {
    // Keep the key in memory for this page if browser storage is unavailable.
  }
}

function requestHeaders(init?: RequestInit): Headers {
  const headers = new Headers(init?.headers);
  const key = getStoredAccessKey();
  if (key && !headers.has("X-Mimi-Key")) headers.set("X-Mimi-Key", key);
  return headers;
}

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: requestHeaders(init),
    });
  } catch {
    throw new ApiError(
      0,
      `Cannot reach the backend at ${API_BASE}. Start it with "uvicorn mimi.api:app --reload" from backend/, or set VITE_API_BASE.`,
    );
  }
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = (await res.json()) as unknown;
      if (typeof body === "object" && body !== null && "detail" in body) {
        const d = (body as { detail: unknown }).detail;
        detail = typeof d === "string" ? d : JSON.stringify(d);
      }
    } catch {
      // keep the status line
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

export async function listReports(limit = 50): Promise<ReportListItem[]> {
  if (USE_MOCK) {
    return [
      {
        id: mockDossier.report_id,
        created_at: mockDossier.created_at,
        source: mockDossier.source,
        package_spec: mockDossier.package_spec,
        status: "complete",
        tier: mockDossier.tier,
      },
    ];
  }
  return request<ReportListItem[]>(`/api/reports?limit=${limit}`);
}

export async function getReport(reportId: string): Promise<Dossier> {
  if (USE_MOCK) {
    if (reportId !== mockDossier.report_id) throw new ApiError(404, "No such report.");
    return mockDossier;
  }
  return request<Dossier>(`/api/reports/${encodeURIComponent(reportId)}`);
}

export async function getEvents(reportId: string): Promise<StageEvent[]> {
  if (USE_MOCK) {
    if (reportId !== mockDossier.report_id) throw new ApiError(404, "No such report.");
    return mockDossier.events;
  }
  return request<StageEvent[]>(
    `/api/reports/${encodeURIComponent(reportId)}/events`,
  );
}

export async function submitReport(
  submission: ReportSubmission,
  accessKey?: string,
): Promise<SubmitResponse> {
  if (USE_MOCK) {
    // Mock mode never accepts submissions; the UI surfaces this clearly.
    throw new ApiError(
      402,
      "Mock mode is read-only. Unset VITE_USE_MOCK to submit live reports.",
    );
  }
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (accessKey && accessKey.trim() !== "") {
    headers["X-Mimi-Key"] = accessKey.trim();
  }
  return request<SubmitResponse>("/api/reports", {
    method: "POST",
    headers,
    body: JSON.stringify(submission),
  });
}

/**
 * Live stage events via SSE (GET /api/reports/{id}/stream).
 * Falls back to polling GET /api/reports/{id}/events when EventSource errors.
 * Returns a cleanup function that stops the stream/polling.
 */
export function streamEvents(
  reportId: string,
  onEvent: (event: StageEvent) => void,
  onFallback?: (reason: string) => void,
  onComplete?: () => void,
): () => void {
  if (USE_MOCK) {
    if (reportId !== mockDossier.report_id) return () => undefined;
    for (const ev of mockDossier.events) onEvent(ev);
    onComplete?.();
    return () => undefined;
  }

  const encoded = encodeURIComponent(reportId);
  let cleaned = false;
  let completed = false;
  let pollTimer: number | null = null;
  let controller: AbortController | null = null;
  // Polling returns the FULL recorded history each tick. Keep a seen-set so a
  // tick only forwards events the timeline has not already received (from a
  // previous tick, or from the live SSE stream before it dropped).
  const seen = new Set<string>();
  const eventKey = (ev: StageEvent): string =>
    `${ev.ts}|${ev.stage}|${ev.status}|${ev.detail ?? ""}`;
  const deliver = (ev: StageEvent) => {
    const key = eventKey(ev);
    if (seen.has(key)) return;
    seen.add(key);
    onEvent(ev);
  };

  const isTerminal = (ev: StageEvent): boolean =>
    ev.stage === "pipeline" && ev.data?.final === true;

  const finish = () => {
    if (cleaned || completed) return;
    completed = true;
    if (pollTimer !== null) {
      window.clearInterval(pollTimer);
      pollTimer = null;
    }
    controller?.abort();
    controller = null;
    onComplete?.();
  };

  const startPolling = (reason: string) => {
    if (cleaned || completed || pollTimer !== null) return;
    if (onFallback) onFallback(reason);
    const poll = async () => {
      try {
        const events = await getEvents(reportId);
        if (cleaned || completed) return;
        for (const ev of events) {
          deliver(ev);
          if (isTerminal(ev)) finish();
        }
      } catch {
        // keep polling; the next tick may succeed
      }
    };
    void poll();
    pollTimer = window.setInterval(() => void poll(), 5000);
  };

  const dispatchFrame = (frame: string): boolean => {
    let eventName = "message";
    const data: string[] = [];
    for (const line of frame.split("\n")) {
      if (line === "" || line.startsWith(":")) continue;
      const separator = line.indexOf(":");
      const field = separator < 0 ? line : line.slice(0, separator);
      let value = separator < 0 ? "" : line.slice(separator + 1);
      if (value.startsWith(" ")) value = value.slice(1);
      if (field === "event") eventName = value;
      else if (field === "data") data.push(value);
    }
    if (eventName === "done") {
      finish();
      return true;
    }
    if (eventName === "message" && data.length > 0) {
      try {
        deliver(JSON.parse(data.join("\n")) as StageEvent);
      } catch {
        // Ignore malformed frames; a later event can still be useful.
      }
    }
    return false;
  };

  const readStream = async () => {
    controller = new AbortController();
    try {
      const headers = new Headers();
      const key = getStoredAccessKey();
      if (key) headers.set("X-Mimi-Key", key);
      const response = await fetch(
        `${API_BASE}/api/reports/${encoded}/stream`,
        { headers, signal: controller.signal },
      );
      if (!response.ok) {
        if (response.status === 401 || response.status === 404) finish();
        else startPolling("live stream unavailable — polling recorded events instead");
        return;
      }
      if (!response.body) {
        startPolling("live stream is unavailable — polling recorded events instead");
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (!cleaned && !completed) {
        const { value, done } = await reader.read();
        if (done) {
          buffer += decoder.decode().replace(/\r\n/g, "\n");
          break;
        }
        buffer += decoder.decode(value, { stream: true });
        // Normalize after appending so a CRLF pair split across network
        // chunks still becomes a frame delimiter.
        buffer = buffer.replace(/\r\n/g, "\n");
        let boundary = buffer.indexOf("\n\n");
        while (boundary >= 0) {
          const frame = buffer.slice(0, boundary);
          buffer = buffer.slice(boundary + 2);
          if (dispatchFrame(frame)) return;
          boundary = buffer.indexOf("\n\n");
        }
      }
      if (!completed && !cleaned && buffer.trim()) dispatchFrame(buffer);
      if (!completed && !cleaned) {
        startPolling("live stream ended early — polling recorded events instead");
      }
    } catch {
      if (!cleaned && !completed) {
        startPolling("live stream unavailable — polling recorded events instead");
      }
    }
  };

  void readStream();

  return () => {
    cleaned = true;
    if (pollTimer !== null) window.clearInterval(pollTimer);
    controller?.abort();
    controller = null;
  };
}

/** GET /api/health — used only for the header status dot. */
export async function health(): Promise<boolean> {
  if (USE_MOCK) return true;
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    return res.ok;
  } catch {
    return false;
  }
}
