import type {
  CompletenessResponse,
  RagResponse,
  TaxFact,
  UserProfile,
} from "./types";

const API_BASE =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ??
  "https://api.tax-gpt.online";

export interface ExtractResponse {
  facts: TaxFact[];
  doc_type?: string;
}

export function extractDocument(
  file: File,
  onProgress?: (pct: number) => void,
): Promise<ExtractResponse> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const fd = new FormData();
    fd.append("file", file);
    xhr.open("POST", `${API_BASE}/api/extract`);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const data = JSON.parse(xhr.responseText);
          // Normalise: accept either { facts: [...] } or a bare array
          const facts: TaxFact[] = Array.isArray(data)
            ? data
            : Array.isArray(data.facts)
              ? data.facts
              : [];
          resolve({ facts: facts.map((f) => ({ ...f, confirmed_by_user: false })), doc_type: data.doc_type });
        } catch (err) {
          reject(new Error("Invalid JSON from /api/extract"));
        }
      } else {
        reject(new Error(`Extract failed (${xhr.status}): ${xhr.responseText}`));
      }
    };
    xhr.onerror = () => reject(new Error("Network error during extract"));
    xhr.send(fd);
  });
}

interface BackendFinding {
  rule_id: string;
  title_en: string;
  message_en: string;
  asks_for: string[];
  source_doc: string;
  pdf_page: number | null;
  severity: "blocker" | "likely_missing" | "nice_to_have";
  verification_status: string;
}

function findingToItem(f: BackendFinding) {
  return {
    code: f.rule_id,
    label: f.title_en,
    reason: f.message_en,
    suggested_doc: f.asks_for?.[0],
  };
}

export async function checkCompleteness(payload: {
  profile: UserProfile;
  confirmed_facts: TaxFact[];
}): Promise<CompletenessResponse> {
  const res = await fetch(`${API_BASE}/api/completeness/check`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Completeness check failed (${res.status})`);
  const data = await res.json();

  // Backend returns list[Finding] (canonical shape from main.py).
  // Partition by severity and remap field names to the UI's
  // CompletenessItem shape. Also tolerate the legacy categorized
  // object shape for forward/backward safety.
  if (Array.isArray(data)) {
    const findings = data as BackendFinding[];
    return {
      missing: findings.filter((f) => f.severity === "blocker").map(findingToItem),
      likely_missing: findings
        .filter((f) => f.severity === "likely_missing")
        .map(findingToItem),
      complete: findings
        .filter((f) => f.severity === "nice_to_have")
        .map(findingToItem),
    };
  }
  return {
    missing: data.missing ?? [],
    likely_missing: data.likely_missing ?? [],
    complete: data.complete ?? [],
  };
}

export async function ragExplain(payload: {
  question: string;
  profile: UserProfile;
  confirmed_facts: TaxFact[];
}): Promise<RagResponse> {
  const res = await fetch(`${API_BASE}/api/rag/explain`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Copilot failed (${res.status})`);
  const data = await res.json();
  return {
    answer_en: data.answer_en ?? "",
    citations: data.citations ?? [],
  };
}

export { API_BASE };