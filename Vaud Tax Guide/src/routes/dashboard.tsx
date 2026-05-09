import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { PageTransition } from "@/components/PageTransition";
import { useAppStore, buildCompletenessPayload } from "@/lib/store";
import { checkCompleteness } from "@/lib/api";
import { AlertCircle, AlertTriangle, CheckCircle2, RefreshCw } from "lucide-react";
import type { CompletenessItem } from "@/lib/types";

export const Route = createFileRoute("/dashboard")({
  head: () => ({ meta: [{ title: "Dashboard — VaudTaxAI" }] }),
  component: DashboardPage,
});

function DashboardPage() {
  const navigate = useNavigate();
  const setCompleteness = useAppStore((s) => s.setCompleteness);
  const payload = useAppStore(buildCompletenessPayload);

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ["completeness", payload],
    queryFn: async () => {
      const res = await checkCompleteness(payload);
      setCompleteness(res);
      return res;
    },
  });

  return (
    <PageTransition>
      <header className="mb-8 flex items-end justify-between gap-4">
        <div>
          <p className="text-sm font-medium uppercase tracking-widest text-primary">Step 5</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">Completeness dashboard</h1>
          <p className="mt-2 text-muted-foreground">
            Vaud-specific rules engine — what's done, what's likely missing, what's missing.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isFetching}>
          <RefreshCw className={`mr-2 h-3.5 w-3.5 ${isFetching ? "animate-spin" : ""}`} />
          Re-check
        </Button>
      </header>

      {isLoading && <p className="text-sm text-muted-foreground">Running checks…</p>}
      {error && (
        <p className="rounded-md border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive">
          {(error as Error).message}
        </p>
      )}

      {data && (
        <div className="grid gap-4 md:grid-cols-3">
          <Column
            tone="missing"
            icon={<AlertCircle className="h-4 w-4 text-destructive" />}
            title="Missing"
            items={data.missing}
          />
          <Column
            tone="amber"
            icon={<AlertTriangle className="h-4 w-4 text-amber-600" />}
            title="Likely missing"
            items={data.likely_missing}
          />
          <Column
            tone="ok"
            icon={<CheckCircle2 className="h-4 w-4 text-success" />}
            title="Complete"
            items={data.complete}
          />
        </div>
      )}

      <div className="mt-10 flex justify-between">
        <Button asChild variant="ghost">
          <Link to="/interview">← Back</Link>
        </Button>
        <Button size="lg" onClick={() => navigate({ to: "/copilot" })}>
          Open copilot →
        </Button>
      </div>
    </PageTransition>
  );
}

function Column({
  tone,
  icon,
  title,
  items,
}: {
  tone: "missing" | "amber" | "ok";
  icon: React.ReactNode;
  title: string;
  items: CompletenessItem[];
}) {
  const ring =
    tone === "missing"
      ? "border-destructive/30 bg-destructive/5"
      : tone === "amber"
        ? "border-amber-300 bg-amber-50"
        : "border-success/30 bg-success/5";
  return (
    <div className={`rounded-lg border p-4 ${ring}`}>
      <div className="mb-3 flex items-center gap-2">
        {icon}
        <h2 className="text-sm font-semibold uppercase tracking-wide">{title}</h2>
        <Badge variant="outline" className="ml-auto">{items.length}</Badge>
      </div>
      {items.length === 0 ? (
        <p className="text-xs text-muted-foreground">Nothing here.</p>
      ) : (
        <ul className="space-y-2">
          {items.map((it) => (
            <li key={it.code} className="rounded-md border bg-background p-3">
              <div className="flex items-center gap-2">
                <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
                  {it.code}
                </span>
                <span className="text-sm font-medium">{it.label}</span>
              </div>
              {it.reason && <p className="mt-1 text-xs text-muted-foreground">{it.reason}</p>}
              {it.suggested_doc && (
                <p className="mt-1 text-xs text-primary">Suggested: {it.suggested_doc}</p>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}