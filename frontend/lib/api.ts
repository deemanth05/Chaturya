export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    credentials: "same-origin",
    headers: {
      ...(init.body && !(init.body instanceof FormData)
        ? { "Content-Type": "application/json" }
        : {}),
      ...init.headers,
    },
  });
  if (!response.ok) {
    if (
      response.status === 401 &&
      path !== "/auth/login" &&
      typeof window !== "undefined"
    )
      window.dispatchEvent(new Event("workbench:session-expired"));
    let message = `${response.status} ${response.statusText}`;
    const body = await response.text();
    try {
      const detail = JSON.parse(body).detail;
      message =
        typeof detail === "string" ? detail : JSON.stringify(detail || body);
    } catch {
      if (body) message = body;
    }
    throw new ApiError(response.status, message);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}
export function date(value?: number) {
  return value
    ? new Date(value * 1000).toLocaleString("en-IN", {
        dateStyle: "medium",
        timeStyle: "short",
      })
    : "Unavailable";
}
export function message(error: unknown) {
  return error instanceof Error ? error.message : String(error);
}
export type User = {
  id: string;
  username: string;
  role: string;
  active?: number;
  created?: number;
};
export type Doc = {
  id: string;
  name: string;
  audience: string;
  status: string;
  department: string;
  course: string;
  version: string;
  language: string;
  extraction: string;
  chunks: number;
  sha256: string;
  created: number;
};
export type Source = {
  id: string;
  document_id: string;
  name: string;
  page: number;
  section: string;
  text: string;
  status: string;
  extraction: string;
  version: string;
  score: number;
};
export type Event = {
  id: number;
  kind: string;
  time: number;
  payload: Record<string, unknown>;
};
export type Result = {
  title: string;
  status: string;
  basis?: string;
  warnings?: string[];
  missing_information?: string[];
  sections: {
    heading: string;
    text: string;
    evidence: { source_id: string; quote: string }[];
  }[];
  sources?: Source[];
};
export type Job = {
  id: string;
  name: string;
  workflow: string;
  status: string;
  created: number;
  updated: number;
  error?: string;
  reviews?: { id: string; username: string; note: string; time: number }[];
  state?: {
    prompt?: string;
    grounding?: string;
    language?: string;
    result?: Result;
    retrieval?: { sources?: Source[]; mode?: string; warning?: string };
    route?: {
      model: string;
      method: string;
      reason: string;
      probabilities?: Record<string, number>;
    };
    artifact?: string;
    verification?: string;
    attempts?: {
      attempt: number;
      status: string;
      error?: string;
      checks?: { case: number; output: unknown; latency_ms: number }[];
    }[];
  };
};
export type System = {
  models: {
    id: string;
    enabled: boolean;
    modalities: string[];
    strengths?: Record<string, number>;
    endpoint?: string;
  }[];
  worker_limit: number;
  model_concurrency: number;
  laya_configured: boolean;
  allowed_origins: string[];
  storage: string;
  monitor: {
    visibility: string;
    scope: string;
    enforcement: string;
    sampled_at: number;
    blocked_attempts: number;
    local_calls: number;
    external_bytes: number | null;
    note: string;
    unexpected_connections: { ip: string; port: number; status: string }[];
  };
};
export type College = {
  workflows: string[];
  teaching_roles: string[];
  letter_roles: string[];
  default_language: string;
};
