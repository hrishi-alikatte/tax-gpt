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
      {/* Swiss cross motif */}
      <div className="mb-6 flex items-center gap-3">
        <div className="flex h-6 w-6 items-center justify-center rounded-sm bg-primary">
          <span className="text-[10px] font-bold text-primary-foreground">+</span>
        </div>
        <span className="text-xs font-medium uppercase tracking-[0.2em] text-primary">
          Canton de Vaud
        </span>
      </div>

      <h1 className="mt-6 max-w-3xl text-4xl font-medium leading-[1.1] tracking-tight md:text-6xl">
        A guided assistant for
        <br />
        your Vaud tax declaration.
      </h1>

      <div className="mt-6 h-px w-16 bg-primary" />

      <p className="mt-6 max-w-2xl text-lg leading-relaxed text-muted-foreground">
        Built for English-speaking C permit holders in Vaud. Upload your tax documents,
        confirm extracted values, and get a checklist and summary based on the official
        Vaud 2025 instructions.
      </p>

      <div className="mt-10 flex flex-wrap gap-3">
        <Button asChild size="lg">
          <Link to="/intake">
            {hasState ? "Continue tax filing" : "Start tax filing"}
            <ArrowRight className="ml-2 h-4 w-4" />
          </Link>
        </Button>
        {hasState && (
          <Button asChild variant="outline" size="lg">
            <Link to="/dashboard">View checklist</Link>
          </Button>
        )}
      </div>

      <div className="mt-24 grid gap-6 md:grid-cols-3">
        <Feature
          icon={<FileCheck2 className="h-5 w-5 text-primary" />}
          title="Upload & confirm"
          body="Upload your salary certificate, health insurance premiums, bank statements, and Pillar 3a certificate. Confirm every extracted value before it is used."
        />
        <Feature
          icon={<Sparkles className="h-5 w-5 text-primary" />}
          title="VaudTax checks"
          body="Get checks for common missing items: salary income, AHV/AVS, occupational pension, Pillar 3a, health insurance, transport, and bank accounts."
        />
        <Feature
          icon={<ShieldCheck className="h-5 w-5 text-primary" />}
          title="Official-source answers"
          body="Ask questions in English and get answers based on the official Vaud 2025 tax instructions, with references to the relevant sections."
        />
      </div>
    </div>
  );
}

function Feature({ icon, title, body }: { icon: React.ReactNode; title: string; body: string }) {
  return (
    <div className="group rounded-lg border bg-card p-6 transition-colors hover:border-primary/30">
      <div className="mb-3 inline-flex h-9 w-9 items-center justify-center rounded-md bg-primary/10">
        {icon}
      </div>
      <h3 className="text-base font-semibold">{title}</h3>
      <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{body}</p>
    </div>
  );
}
