import type {
  CompletenessResponse,
  RagResponse,
  TaxFact,
  UserProfile,
} from "./types";

const API_BASE =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ??
  "https://vaudtaxai-web-410743045655.europe-west6.run.app";

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