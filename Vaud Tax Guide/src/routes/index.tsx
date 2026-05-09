import { createFileRoute } from "@tanstack/react-router";
import { Link } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { useAppStore } from "@/lib/store";
import { ArrowRight, FileCheck2, Sparkles, ShieldCheck } from "lucide-react";

export const Route = createFileRoute("/")({
  component: Index,
});

function Index() {
  const hasState = useAppStore((s) => !!s.profile.first_name || s.documents.length > 0);
  return (
    <div className="mx-auto max-w-5xl px-6 py-16 md:py-24">
      <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-widest text-primary">
        <span className="h-2 w-2 rounded-full bg-primary" />
        Canton de Vaud
      </div>
      <h1 className="mt-6 text-4xl font-semibold leading-tight tracking-tight md:text-6xl">
        Your guided copilot for the
        <br />
        <span className="text-primary">Vaud tax declaration.</span>
      </h1>
      <p className="mt-6 max-w-2xl text-lg text-muted-foreground">
        Built for English-speaking C-Permit holders. Upload your documents, confirm what we
        extracted, and get a complete, source-grounded summary ready for VaudTax.
      </p>
      <div className="mt-10 flex flex-wrap gap-3">
        <Button asChild size="lg">
          <Link to="/intake">
            {hasState ? "Resume filing" : "Start filing"} <ArrowRight className="ml-2 h-4 w-4" />
          </Link>
        </Button>
        {hasState && (
          <Button asChild variant="outline" size="lg">
            <Link to="/dashboard">Open dashboard</Link>
          </Button>
        )}
      </div>

      <div className="mt-20 grid gap-6 md:grid-cols-3">
        <Feature
          icon={<FileCheck2 className="h-5 w-5 text-primary" />}
          title="Extract & confirm"
          body="Drop in your salary certificate, Pillar 3a, health insurance — every value must be confirmed before it counts."
        />
        <Feature
          icon={<Sparkles className="h-5 w-5 text-primary" />}
          title="Vaud-aware checks"
          body="A deterministic rules engine flags missing AVS/LPP, Pillar 3a, and commune-specific deductions."
        />
        <Feature
          icon={<ShieldCheck className="h-5 w-5 text-primary" />}
          title="Sourced answers"
          body="The copilot cites the official Vaud 2025 instructions — no guessing, no IRS, no 401k."
        />
      </div>
    </div>
  );
}

function Feature({ icon, title, body }: { icon: React.ReactNode; title: string; body: string }) {
  return (
    <div className="rounded-lg border bg-card p-6">
      <div className="mb-3 inline-flex h-9 w-9 items-center justify-center rounded-md bg-primary/10">
        {icon}
      </div>
      <h3 className="text-base font-semibold">{title}</h3>
      <p className="mt-2 text-sm text-muted-foreground">{body}</p>
    </div>
  );
}
