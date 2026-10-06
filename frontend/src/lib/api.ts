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
    res = await fetch(`${API_BASE}${path}`, init);
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
  if (USE_MOCK) return mockDossier;
  return request<Dossier>(`/api/reports/${encodeURIComponent(reportId)}`);
}

export async function getEvents(reportId: string): Promise<StageEvent[]> {
  if (USE_MOCK) return mockDossier.events;
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
): () => void {
  if (USE_MOCK) {
    for (const ev of mockDossier.events) onEvent(ev);
    return () => undefined;
  }

  const encoded = encodeURIComponent(reportId);
  let cleaned = false;
  let pollTimer: number | null = null;
  let source: EventSource | null = null;

  const startPolling = (reason: string) => {
    if (cleaned || pollTimer !== null) return;
    if (onFallback) onFallback(reason);
    const poll = async () => {
      try {
        const events = await getEvents(reportId);
        if (cleaned) return;
        for (const ev of events) onEvent(ev);
      } catch {
        // keep polling; the next tick may succeed
      }
    };
    void poll();
    pollTimer = window.setInterval(() => void poll(), 5000);
  };

  try {
    source = new EventSource(`${API_BASE}/api/reports/${encoded}/stream`);
    source.onmessage = (msg: MessageEvent<string>) => {
      try {
        onEvent(JSON.parse(msg.data) as StageEvent);
      } catch {
        // ignore malformed frames (keep-alives are comments, not messages)
      }
    };
    source.onerror = () => {
      source?.close();
      source = null;
      startPolling("live stream unavailable — polling recorded events instead");
    };
  } catch {
    startPolling("EventSource could not be created — polling instead");
  }

  return () => {
    cleaned = true;
    if (pollTimer !== null) window.clearInterval(pollTimer);
    if (source !== null) source.close();
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
