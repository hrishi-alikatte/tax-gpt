import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { PageTransition } from "@/components/PageTransition";
import { useAppStore } from "@/lib/store";

export const Route = createFileRoute("/interview")({
  head: () => ({ meta: [{ title: "Interview — VaudTaxAI" }] }),
  component: InterviewPage,
});

function InterviewPage() {
  const navigate = useNavigate();
  const interview = useAppStore((s) => s.interview);
  const setInterview = useAppStore((s) => s.setInterview);
  const profile = useAppStore((s) => s.profile);

  const ready =
    interview.foreign_assets !== null &&
    interview.lpp_buyback !== null &&
    (profile.has_workplace_canteen ? !!interview.meal_allowance_method : true);

  return (
    <PageTransition>
      <header className="mb-8">
        <p className="text-sm font-medium uppercase tracking-widest text-primary">Step 4</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">A few targeted questions</h1>
        <p className="mt-2 text-muted-foreground">
          These trigger Vaud-specific rules that documents alone can't reveal.
        </p>
      </header>

      <div className="space-y-6 rounded-lg border bg-card p-6">
        <Question
          label="Do you hold any foreign assets (bank accounts, real estate, securities) outside Switzerland?"
          value={interview.foreign_assets}
          onChange={(v) => setInterview({ foreign_assets: v })}
        />
        <Question
          label="Did you make any voluntary 2nd Pillar (LPP) buy-back contributions in 2024?"
          value={interview.lpp_buyback}
          onChange={(v) => setInterview({ lpp_buyback: v })}
        />

        {profile.has_workplace_canteen && (
          <div className="space-y-3">
            <Label className="text-sm font-medium">
              How do you handle meal expenses?
            </Label>
            <RadioGroup
              value={interview.meal_allowance_method ?? ""}
              onValueChange={(v) =>
                setInterview({ meal_allowance_method: v as "canteen" | "lump_sum" | "none" })
              }
              className="space-y-2"
            >
              <Option value="canteen" label="Subsidised canteen at work" />
              <Option value="lump_sum" label="Lump-sum meal deduction (CHF 1 600 / year)" />
              <Option value="none" label="None — I eat at home" />
            </RadioGroup>
          </div>
        )}
      </div>

      <div className="mt-10 flex justify-between">
        <Button asChild variant="ghost">
          <Link to="/review">← Back</Link>
        </Button>
        <Button
          size="lg"
          disabled={!ready}
          onClick={() => navigate({ to: "/dashboard" })}
        >
          Run completeness check
        </Button>
      </div>
    </PageTransition>
  );
}

function Question({
  label,
  value,
  onChange,
}: {
  label: string;
  value: boolean | null;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="space-y-3">
      <Label className="text-sm font-medium">{label}</Label>
      <RadioGroup
        value={value === null ? "" : value ? "yes" : "no"}
        onValueChange={(v) => onChange(v === "yes")}
        className="flex gap-6"
      >
        <Option value="yes" label="Yes" />
        <Option value="no" label="No" />
      </RadioGroup>
    </div>
  );
}

function Option({ value, label }: { value: string; label: string }) {
  const id = `opt-${value}-${label.replace(/\s+/g, "-")}`;
  return (
    <div className="flex items-center gap-2">
      <RadioGroupItem value={value} id={id} />
      <Label htmlFor={id} className="cursor-pointer text-sm font-normal">{label}</Label>
    </div>
  );
}