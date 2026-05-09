import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { PageTransition } from "@/components/PageTransition";
import { DocumentCard } from "@/components/DocumentCard";
import { useAppStore, selectAllFactsConfirmed } from "@/lib/store";

export const Route = createFileRoute("/review")({
  head: () => ({ meta: [{ title: "Review — VaudTaxAI" }] }),
  component: ReviewPage,
});

function ReviewPage() {
  const navigate = useNavigate();
  const documents = useAppStore((s) => s.documents);
  const allConfirmed = useAppStore(selectAllFactsConfirmed);

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
          Confirm every value before continuing. Only confirmed facts are sent to the rules engine.
          {totalFacts > 0 && (
            <span className="ml-1 font-medium text-foreground">
              ({confirmedFacts}/{totalFacts} confirmed)
            </span>
          )}
        </p>
      </header>

      {documents.length === 0 ? (
        <div className="rounded-lg border border-dashed bg-card p-10 text-center">
          <p className="text-sm text-muted-foreground">No documents yet.</p>
          <Button asChild className="mt-4"><Link to="/upload">Upload documents</Link></Button>
        </div>
      ) : (
        <div className="space-y-4">
          {documents.map((d) => (
            <DocumentCard key={d.id} doc={d} />
          ))}
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
        >
          Continue to interview
        </Button>
      </div>
    </PageTransition>
  );
}