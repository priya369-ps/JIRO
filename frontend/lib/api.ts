export type Provider = "groq" | "byok" | "local";

export type Requirement = {
  value: string;
  category: string;
  status: string;
  evidence: string | null;
  confidence: number;
};

export type TailoringResponse = {
  tailored_resume: string;
  job_requirements: Requirement[];
  matches: Requirement[];
  gaps: Requirement[];
  validation: {
    status: string;
    warnings: string[];
    export_blocked: boolean;
    ats_risks: string[];
  };
  diff: { changed: boolean; unified: string; summary: string };
  exports: { format: string; available: boolean; content: string | null; reason: string | null }[];
  workflow: {
    state: string;
    privacy_mode: string;
    validation_status: string;
    warnings_present: boolean;
    export_blocked: boolean;
    available_exports: string[];
  };
};

const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${baseUrl}${path}`, { ...init, headers: { "Content-Type": "application/json", ...init?.headers } });
  } catch {
    throw new Error("JIRO backend is unavailable. Start the API and try again.");
  }
  const payload = await response.json().catch(() => ({ detail: "Backend returned an unreadable response." }));
  if (!response.ok) throw new Error(typeof payload.detail === "string" ? payload.detail : "Request failed safely.");
  return payload as T;
}

export function tailor(resume: string, jobDescription: string, provider: Provider): Promise<TailoringResponse> {
  return request<TailoringResponse>("/tailor", { method: "POST", body: JSON.stringify({ resume, job_description: jobDescription, provider, privacy_mode: "ephemeral" }) });
}

export async function ingestFile(file: File, provider: Provider): Promise<{ normalized_text: string }> {
  const form = new FormData();
  form.append("file", file);
  form.append("provider", provider);
  const response = await fetch(`${baseUrl}/ingest/file`, { method: "POST", body: form });
  const payload = await response.json().catch(() => ({ detail: "Backend returned an unreadable response." }));
  if (!response.ok) throw new Error(typeof payload.detail === "string" ? payload.detail : "File ingestion failed safely.");
  return payload as { normalized_text: string };
}

export function health(): Promise<{ status: string; configuration: Record<string, unknown> }> {
  return request("/health");
}
