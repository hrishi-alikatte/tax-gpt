import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Check, FileCheck, AlertCircle, FileText } from "lucide-react";
import { PageTransition } from "@/components/PageTransition";
import { DocumentCard } from "@/components/DocumentCard";
import { useAppStore, selectAllFactsConfirmed } from "@/lib/store";
import { lookupCode, formatFactValue } from "@/lib/vaud-codes";
import type { TaxFact } from "@/lib/types";

export const Route = createFileRoute("/review")({
  head: () => ({ meta: [{ title: "Review — VaudTaxAI" }] }),
  component: ReviewPage,
});

function ReviewPage() {
  const navigate = useNavigate();
  const documents = useAppStore((s) => s.documents.filter((d) => d.status === "ready"));
  const allConfirmed = useAppStore(selectAllFactsConfirmed);

  const [selected, setSelected] = useState<{ docId: string; canonical: string } | null>(null);

  const selectedFact: TaxFact | null = useMemo(() => {
    if (!selected) return null;
    const doc = documents.find((d) => d.id === selected.docId);
    return doc?.facts.find((f) => f.canonical_field === selected.canonical) ?? null;
  }, [selected, documents]);

  const totalFacts = documents.reduce((n, d) => n + d.facts.length, 0);
  const confirmedFacts = documents.reduce(
    (n, d) => n + d.facts.filter((f) => f.confirmed_by_user).length,
    0,
  );

  return (
    <PageTransition>
      <header className="mb-8">
        <p className="text-sm font-medium uppercase tracking-widest text-primary">Step 3</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">Review extracted facts</h1>
        <p className="mt-2 text-muted-foreground">
          Confirm or correct every value. Click a fact to inspect source details.
          {totalFacts > 0 && (
            <span className="ml-1 font-medium text-foreground">
              ({confirmedFacts}/{totalFacts} confirmed)
            </span>
          )}
        </p>
      </header>

      {documents.length === 0 ? (
        <div className="rounded-lg border border-dashed bg-card p-10 text-center">
          <FileText className="mx-auto h-8 w-8 text-muted-foreground/50" />
          <p className="mt-3 text-sm text-muted-foreground">No documents ready for review yet.</p>
          <Button asChild className="mt-4"><Link to="/upload">Upload documents</Link></Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
          {/* Left — document list */}
          <div className="space-y-4 lg:col-span-3">
            {documents.map((doc) => (
              <DocumentCard
                key={doc.id}
                doc={doc}
                selectedFact={selected}
                onSelectFact={(docId, canonical) => setSelected({ docId, canonical })}
              />
            ))}
          </div>

          {/* Right — detail panel */}
          <aside className="lg:col-span-2">
            <div className="sticky top-6 space-y-4">
              {selectedFact ? (
                <FactDetailPanel
                  fact={selectedFact}
                  onClose={() => setSelected(null)}
                />
              ) : (
                <div className="rounded-lg border bg-card p-6 text-center">
                  <AlertCircle className="mx-auto h-8 w-8 text-muted-foreground/50" />
                  <p className="mt-3 text-sm font-medium text-muted-foreground">
                    Select a fact to view details
                  </p>
                </div>
              )}
            </div>
          </aside>
        </div>
      )}

      <div className="mt-10 flex justify-between">
        <Button asChild variant="ghost">
          <Link to="/upload">← Back</Link>
        </Button>
        <Button
          size="lg"
          disabled={!allConfirmed}
          onClick={() => navigate({ to: "/interview" })}
          className="gap-2"
        >
          <FileCheck className="h-4 w-4" />
          {allConfirmed ? "All confirmed — continue" : "Confirm all facts to continue"}
        </Button>
      </div>
    </PageTransition>
  );
}

function FactDetailPanel({ fact, onClose }: { fact: TaxFact; onClose: () => void }) {
  const toggle = useAppStore((s) => s.toggleFactConfirm);
  const edit = useAppStore((s) => s.editFact);
  const doc = useAppStore((s) =>
    s.documents.find((d) => d.facts.some((f) => f.canonical_field === fact.canonical_field)),
  );
  const docId = doc?.id ?? "";

  const code = lookupCode(fact.canonical_field);
  const conf = Math.round((fact.confidence ?? 0) * 100);
  const methodLabels: Record<string, string> = {
    regex: "Pattern match",
    pdf_text: "PDF text",
    ocr: "OCR",
    llm_structured: "AI extraction",
  };

  return (
    <div className="rounded-lg border bg-card p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] font-medium text-muted-foreground">
              {code.code}
            </span>
            <h3 className="text-sm font-semibold">{code.label}</h3>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">{fact.canonical_field}</p>
        </div>
        <Button variant="ghost" size="sm" onClick={onClose}>
          Close
        </Button>
      </div>

      <div className="mt-4 space-y-3">
        <DetailRow label="Extracted value">
          <span className="text-lg font-semibold tabular-nums">
            {formatFactValue(fact.canonical_field, fact.value)}
          </span>
        </DetailRow>

        <DetailRow label="Source document">
          <span className="text-sm">{fact.source_doc}</span>
        </DetailRow>

        {fact.source_page ? (
          <DetailRow label="Source page">
            <span className="text-sm font-medium">{fact.source_page}</span>
          </DetailRow>
        ) : null}

        <DetailRow label="Confidence">
          <span
            className={`inline-flex items-center rounded px-1.5 py-0.5 text-[11px] font-medium ${
              conf >= 90
                ? "bg-success/15 text-success"
                : conf >= 70
                ? "bg-amber-100 text-amber-800"
                : "bg-destructive/10 text-destructive"
            }`}
          >
            {conf}%
          </span>
        </DetailRow>

        <DetailRow label="Method">
          <span className="text-xs text-muted-foreground">
            {methodLabels[fact.extraction_method] ?? fact.extraction_method}
          </span>
        </DetailRow>

        <DetailRow label="Status">
          <span
            className={`inline-flex items-center gap-1 text-xs font-medium ${
              fact.confirmed_by_user ? "text-success" : "text-muted-foreground"
            }`}
          >
            {fact.confirmed_by_user ? (
              <><Check className="h-3.5 w-3.5" /> Confirmed</>
            ) : (
              "Unconfirmed"
            )}
          </span>
        </DetailRow>
      </div>

      <div className="mt-5 flex gap-2">
        {!fact.confirmed_by_user && (
          <Button
            className="flex-1 gap-1"
            onClick={() => toggle(docId, fact.canonical_field)}
          >
            <Check className="h-3.5 w-3.5" />
            Confirm
          </Button>
        )}
        <Button
          variant="outline"
          className="flex-1"
          onClick={() => {
            const next = prompt("Correct value:", String(fact.value));
            if (next === null) return;
            const num = Number(next);
            const value: TaxFact["value"] =
              !Number.isNaN(num) && next.trim() !== "" ? num : next;
            edit(docId, fact.canonical_field, value);
          }}
        >
          Correct
        </Button>
      </div>
    </div>
  );
}

function DetailRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between border-b pb-2 last:border-0 last:pb-0">
      <span className="text-xs text-muted-foreground">{label}</span>
      {children}
    </div>
  );
}
