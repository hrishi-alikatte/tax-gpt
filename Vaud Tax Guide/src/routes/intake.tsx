import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { PageTransition } from "@/components/PageTransition";
import { useAppStore } from "@/lib/store";
import type { MaritalStatus } from "@/lib/types";

export const Route = createFileRoute("/intake")({
  head: () => ({ meta: [{ title: "Intake — VaudTaxAI" }] }),
  component: IntakePage,
});

const schema = z.object({
  first_name: z.string().min(1, "Required"),
  marital_status: z.enum(["single", "married", "divorced", "widowed", "registered_partnership"]),
  spouse_works: z.boolean(),
  children_count: z.number().min(0).max(15),
  commune_of_residence: z.string().min(1, "Required"),
  employer_name: z.string().min(1, "Required"),
  work_commune: z.string().min(1, "Required"),
  has_workplace_canteen: z.boolean(),
});

type FormVals = z.infer<typeof schema>;

function IntakePage() {
  const navigate = useNavigate();
  const profile = useAppStore((s) => s.profile);
  const setProfile = useAppStore((s) => s.setProfile);

  const { register, handleSubmit, watch, setValue, formState: { errors } } = useForm<FormVals>({
    resolver: zodResolver(schema),
    defaultValues: {
      first_name: profile.first_name ?? "",
      marital_status: (profile.marital_status ?? "single") as MaritalStatus,
      spouse_works: profile.spouse_works ?? false,
      children_count: profile.children_count ?? 0,
      commune_of_residence: profile.commune_of_residence ?? "",
      employer_name: profile.employer_name ?? "",
      work_commune: profile.work_commune ?? "",
      has_workplace_canteen: profile.has_workplace_canteen ?? false,
    },
  });

  const marital = watch("marital_status");
  const showSpouse = marital === "married" || marital === "registered_partnership";

  const onSubmit = (vals: FormVals) => {
    setProfile({
      ...profile,
      first_name: vals.first_name,
      marital_status: vals.marital_status,
      spouse_works: showSpouse ? vals.spouse_works : null,
      children_count: vals.children_count,
      children_ages: profile.children_ages ?? [],
      commune_of_residence: vals.commune_of_residence,
      employer_name: vals.employer_name,
      work_commune: vals.work_commune,
      has_workplace_canteen: vals.has_workplace_canteen,
    });
    navigate({ to: "/upload" });
  };

  return (
    <PageTransition>
      <header className="mb-8">
        <p className="text-sm font-medium uppercase tracking-widest text-primary">Step 1</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">Tell us about you</h1>
        <p className="mt-2 text-muted-foreground">
          A few questions about your household and employment in Canton Vaud.
        </p>
      </header>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6 rounded-lg border bg-card p-6">
        <Field label="First name" error={errors.first_name?.message}>
          <Input {...register("first_name")} placeholder="Marie" />
        </Field>

        <Field label="Marital status" error={errors.marital_status?.message}>
          <Select
            value={marital}
            onValueChange={(v) => setValue("marital_status", v as MaritalStatus, { shouldValidate: true })}
          >
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="single">Single</SelectItem>
              <SelectItem value="married">Married</SelectItem>
              <SelectItem value="registered_partnership">Registered partnership</SelectItem>
              <SelectItem value="divorced">Divorced</SelectItem>
              <SelectItem value="widowed">Widowed</SelectItem>
            </SelectContent>
          </Select>
        </Field>

        {showSpouse && (
          <Field label="Does your spouse / partner also work in Switzerland?">
            <div className="flex items-center gap-3">
              <Switch
                checked={watch("spouse_works")}
                onCheckedChange={(v) => setValue("spouse_works", v)}
              />
              <span className="text-sm text-muted-foreground">{watch("spouse_works") ? "Yes" : "No"}</span>
            </div>
          </Field>
        )}

        <Field label="Number of dependent children" error={errors.children_count?.message}>
          <Input type="number" min={0} max={15} {...register("children_count", { valueAsNumber: true })} className="w-32" />
        </Field>

        <div className="grid gap-6 md:grid-cols-2">
          <Field label="Commune of residence" error={errors.commune_of_residence?.message}>
            <Input {...register("commune_of_residence")} placeholder="Lausanne" />
          </Field>
          <Field label="Work commune" error={errors.work_commune?.message}>
            <Input {...register("work_commune")} placeholder="Renens" />
          </Field>
        </div>

        <Field label="Employer name" error={errors.employer_name?.message}>
          <Input {...register("employer_name")} placeholder="Acme SA" />
        </Field>

        <Field label="Does your workplace have a subsidised canteen?">
          <div className="flex items-center gap-3">
            <Switch
              checked={watch("has_workplace_canteen")}
              onCheckedChange={(v) => setValue("has_workplace_canteen", v)}
            />
            <span className="text-sm text-muted-foreground">
              {watch("has_workplace_canteen") ? "Yes" : "No"}
            </span>
          </div>
        </Field>

        <div className="flex justify-between border-t pt-6">
          <Button asChild variant="ghost">
            <Link to="/">← Home</Link>
          </Button>
          <Button type="submit" size="lg">Continue to upload</Button>
        </div>
      </form>
    </PageTransition>
  );
}

function Field({
  label,
  error,
  children,
}: {
  label: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-2">
      <Label className="text-sm font-medium">{label}</Label>
      {children}
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}