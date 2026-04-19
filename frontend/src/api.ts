import type { ApiError, PlanResponse } from "./types";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL?.trim() || "/api";

export class PlanError extends Error {
  code: string;
  status: number;
  constructor(message: string, code: string, status: number) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

export async function postPlan(prompt: string, signal?: AbortSignal): Promise<PlanResponse> {
  const resp = await fetch(`${API_BASE}/plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt }),
    signal,
  });

  if (!resp.ok) {
    let message = `Request failed (${resp.status})`;
    let code = "request_failed";
    try {
      const body = (await resp.json()) as ApiError | { detail?: unknown };
      if ("error" in body && body.error) {
        code = body.error;
        message = body.detail || body.error;
      } else if ("detail" in body && body.detail) {
        message = Array.isArray(body.detail)
          ? "Invalid request."
          : String(body.detail);
      }
    } catch {
      // non-JSON error body — fall through with defaults
    }
    throw new PlanError(message, code, resp.status);
  }

  return (await resp.json()) as PlanResponse;
}
