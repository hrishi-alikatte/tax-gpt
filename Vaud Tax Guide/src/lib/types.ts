export type MaritalStatus =
  | "single"
  | "married"
  | "divorced"
  | "widowed"
  | "registered_partnership";

export interface UserProfile {
  first_name: string | null;
  permit_type: "C";
  marital_status: MaritalStatus | null;
  spouse_works: boolean | null;
  children_count: number;
  children_ages: number[];
  commune_of_residence: string | null;
  employer_name: string | null;
  work_commune: string | null;
  tax_year: 2024;
  has_workplace_canteen: boolean | null;
}

export interface TaxFact {
  canonical_field: string;
  value: number | string | boolean;
  source_doc: string;
  source_page: number;
  confidence: number;
  extraction_method: "regex" | "pdf_text" | "ocr" | "llm_structured";
  confirmed_by_user: boolean;
}

export type DocStatus = "uploading" | "classifying" | "ready" | "error";

export interface UploadedDoc {
  id: string;
  filename: string;
  status: DocStatus;
  progress: number;
  facts: TaxFact[];
  error?: string;
}

export interface InterviewAnswers {
  foreign_assets: boolean | null;
  lpp_buyback: boolean | null;
  meal_allowance_method?: "canteen" | "lump_sum" | "none" | null;
}

export interface CompletenessItem {
  code: string;
  label: string;
  reason?: string;
  suggested_doc?: string;
}

export interface CompletenessResponse {
  missing: CompletenessItem[];
  likely_missing: CompletenessItem[];
  complete: CompletenessItem[];
}

export interface RagCitation {
  token: string;
  section_title: string;
  page?: number;
}

export interface RagResponse {
  answer_en: string;
  citations: RagCitation[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  citations?: RagCitation[];
}

export const EMPTY_PROFILE: UserProfile = {
  first_name: null,
  permit_type: "C",
  marital_status: null,
  spouse_works: null,
  children_count: 0,
  children_ages: [],
  commune_of_residence: null,
  employer_name: null,
  work_commune: null,
  tax_year: 2024,
  has_workplace_canteen: null,
};

export const EMPTY_INTERVIEW: InterviewAnswers = {
  foreign_assets: null,
  lpp_buyback: null,
  meal_allowance_method: null,
};
