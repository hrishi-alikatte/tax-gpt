import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo } from "react";
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
  errorComponent: ({ error }) => (
    <div className="rounded-md border border-destructive/40 bg-destructive/5 p-6">
      <h2 className="text-lg font-semibold text-destructive">Dashboard error</h2>
      <p className="mt-2 text-sm text-muted-foreground">
        The completeness dashboard failed to render. The check above runs against
        <code className="mx-1 rounded bg-muted px-1.5 py-0.5 font-mono text-[11px]">
          /api/completeness/check
        </code>
        on
        <code className="mx-1 rounded bg-muted px-1.5 py-0.5 font-mono text-[11px]">
          {(import.meta.env.VITE_API_BASE_URL as string) ?? "https://api.tax-gpt.online"}
        </code>
        — confirm the API is reachable.
      </p>
      <pre className="mt-3 overflow-x-auto rounded border bg-background p-3 text-xs">
        {(error as Error).message}
      </pre>
    </div>
  ),
});

function DashboardPage() {
  const navigate = useNavigate();
  const setCompleteness = useAppStore((s) => s.setCompleteness);

  // Subscribe to primitive store slices; each has a stable reference until
  // its own contents change. `buildCompletenessPayload` MUST NOT be passed
  // directly to `useAppStore` — it constructs a new object on every call,
  // which would flip the React Query queryKey identity every render and
  // cause an infinite refetch loop (React error #185).
  const profile = useAppStore((s) => s.profile);
  const documents = useAppStore((s) => s.documents);
  const interview = useAppStore((s) => s.interview);

  const payload = useMemo(
    () => buildCompletenessPayload({ profile, documents, interview } as never),
    [profile, documents, interview],
  );

  // Hash the payload by content so the query refetches when fact set or
  // profile actually changes, not when an upstream selector returned a
  // structurally-equal but referentially-new object.
  const queryHash = useMemo(() => JSON.stringify(payload), [payload]);

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ["completeness", queryHash],
    queryFn: () => checkCompleteness(payload),
  });

  // Mirror the latest result into the global store for downstream
  // consumers (copilot, analytics). Doing this here instead of inside
  // `queryFn` removes the loop: a store write no longer changes any input
  // that the query depends on.
  useEffect(() => {
    if (data) setCompleteness(data);
  }, [data, setCompleteness]);

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
        <div className="grid items-start gap-4 md:grid-cols-3">
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
              <div className="flex min-w-0 items-start gap-2">
                <span className="shrink-0 rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
                  {it.code}
                </span>
                <span className="min-w-0 flex-1 break-all text-sm font-medium">{it.label}</span>
              </div>
              {it.reason && (
                <p className="mt-1 break-all text-xs text-muted-foreground">{it.reason}</p>
              )}
              {it.suggested_doc && (
                <p className="mt-1 break-all text-xs text-primary">Suggested: {it.suggested_doc}</p>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}