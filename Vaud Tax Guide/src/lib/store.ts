import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import {
  EMPTY_INTERVIEW,
  EMPTY_PROFILE,
  type ChatMessage,
  type CompletenessResponse,
  type InterviewAnswers,
  type TaxFact,
  type UploadedDoc,
  type UserProfile,
} from "./types";

interface AppState {
  profile: UserProfile;
  documents: UploadedDoc[];
  interview: InterviewAnswers;
  completeness: CompletenessResponse | null;
  chatHistory: ChatMessage[];

  setProfile: (p: UserProfile) => void;
  addDocument: (doc: UploadedDoc) => void;
  updateDocument: (id: string, patch: Partial<UploadedDoc>) => void;
  removeDocument: (id: string) => void;
  toggleFactConfirm: (docId: string, canonical: string) => void;
  confirmAllInDoc: (docId: string) => void;
  editFact: (docId: string, canonical: string, value: TaxFact["value"]) => void;
  setInterview: (patch: Partial<InterviewAnswers>) => void;
  setCompleteness: (c: CompletenessResponse | null) => void;
  appendChat: (m: ChatMessage) => void;
  reset: () => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      profile: EMPTY_PROFILE,
      documents: [],
      interview: EMPTY_INTERVIEW,
      completeness: null,
      chatHistory: [],

      setProfile: (profile) => set({ profile }),
      addDocument: (doc) => set((s) => ({ documents: [...s.documents, doc] })),
      updateDocument: (id, patch) =>
        set((s) => ({
          documents: s.documents.map((d) => (d.id === id ? { ...d, ...patch } : d)),
        })),
      removeDocument: (id) =>
        set((s) => ({ documents: s.documents.filter((d) => d.id !== id) })),
      toggleFactConfirm: (docId, canonical) =>
        set((s) => ({
          documents: s.documents.map((d) =>
            d.id !== docId
              ? d
              : {
                  ...d,
                  facts: d.facts.map((f) =>
                    f.canonical_field === canonical
                      ? { ...f, confirmed_by_user: !f.confirmed_by_user }
                      : f,
                  ),
                },
          ),
        })),
      confirmAllInDoc: (docId) =>
        set((s) => ({
          documents: s.documents.map((d) =>
            d.id !== docId
              ? d
              : { ...d, facts: d.facts.map((f) => ({ ...f, confirmed_by_user: true })) },
          ),
        })),
      editFact: (docId, canonical, value) =>
        set((s) => ({
          documents: s.documents.map((d) =>
            d.id !== docId
              ? d
              : {
                  ...d,
                  facts: d.facts.map((f) =>
                    f.canonical_field === canonical
                      ? { ...f, value, confirmed_by_user: true, confidence: 1 }
                      : f,
                  ),
                },
          ),
        })),
      setInterview: (patch) =>
        set((s) => ({ interview: { ...s.interview, ...patch } })),
      setCompleteness: (completeness) => set({ completeness }),
      appendChat: (m) => set((s) => ({ chatHistory: [...s.chatHistory, m] })),
      reset: () =>
        set({
          profile: EMPTY_PROFILE,
          documents: [],
          interview: EMPTY_INTERVIEW,
          completeness: null,
          chatHistory: [],
        }),
    }),
    {
      name: "vaudtax-state-v1",
      storage: createJSONStorage(() =>
        typeof window !== "undefined" ? window.localStorage : (undefined as never),
      ),
      skipHydration: true,
    },
  ),
);

// Selectors
export const selectConfirmedFacts = (s: AppState): TaxFact[] =>
  s.documents.flatMap((d) => d.facts.filter((f) => f.confirmed_by_user));

export const selectAllFactsConfirmed = (s: AppState): boolean => {
  const docs = s.documents.filter((d) => d.status === "ready");
  if (docs.length === 0) return false;
  return docs.every((d) => d.facts.length > 0 && d.facts.every((f) => f.confirmed_by_user));
};

/**
 * Merges interview answers into the confirmed_facts array as synthetic TaxFacts.
 * Backend accepts only { profile, confirmed_facts } — interview is folded in here.
 */
export function buildCompletenessPayload(s: AppState) {
  const confirmed = selectConfirmedFacts(s);
  const synthetic: TaxFact[] = [];

  if (s.interview.foreign_assets !== null) {
    synthetic.push({
      canonical_field: "foreign_assets.declared",
      value: s.interview.foreign_assets,
      source_doc: "interview",
      confidence: 1,
      confirmed_by_user: true,
    });
  }
  if (s.interview.lpp_buyback !== null) {
    synthetic.push({
      canonical_field: "pillar_2.buyback_declared",
      value: s.interview.lpp_buyback,
      source_doc: "interview",
      confidence: 1,
      confirmed_by_user: true,
    });
  }
  if (s.interview.meal_allowance_method) {
    synthetic.push({
      canonical_field: "meal_allowance.method",
      value: s.interview.meal_allowance_method,
      source_doc: "interview",
      confidence: 1,
      confirmed_by_user: true,
    });
  }

  return {
    profile: s.profile,
    confirmed_facts: [...confirmed, ...synthetic],
  };
}

/** Step gating */
export function canAdvanceTo(step: number, s: AppState): boolean {
  if (step <= 1) return true;
  const profileOk = !!s.profile.first_name && !!s.profile.marital_status && !!s.profile.commune_of_residence;
  if (step === 2) return profileOk;
  if (step === 3) return profileOk && s.documents.length > 0;
  if (step === 4) return profileOk && selectAllFactsConfirmed(s);
  if (step === 5) return profileOk && selectAllFactsConfirmed(s);
  if (step === 6) return profileOk && selectAllFactsConfirmed(s);
  return false;
}