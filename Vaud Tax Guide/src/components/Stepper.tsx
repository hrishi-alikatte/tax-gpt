import { Link, useLocation } from "@tanstack/react-router";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore, canAdvanceTo } from "@/lib/store";

const STEPS = [
  { n: 1, label: "Intake", path: "/intake" },
  { n: 2, label: "Upload", path: "/upload" },
  { n: 3, label: "Review", path: "/review" },
  { n: 4, label: "Interview", path: "/interview" },
  { n: 5, label: "Dashboard", path: "/dashboard" },
  { n: 6, label: "Copilot", path: "/copilot" },
] as const;

export function Stepper() {
  const location = useLocation();
  const state = useAppStore();

  const currentStep =
    STEPS.find((s) => s.path === location.pathname)?.n ?? 0;

  if (currentStep === 0) return null;

  return (
    <nav className="border-b bg-background">
      <ol className="mx-auto flex max-w-5xl items-center gap-2 px-4 py-4 md:gap-4 md:px-8">
        {STEPS.map((s, i) => {
          const isActive = currentStep === s.n;
          const isDone = currentStep > s.n;
          const canGo = canAdvanceTo(s.n, state);
          const inner = (
            <div className="flex items-center gap-2">
              <span
                className={cn(
                  "flex h-7 w-7 items-center justify-center rounded-full border text-xs font-medium tabular-nums",
                  isActive && "border-primary bg-primary text-primary-foreground",
                  isDone && "border-primary bg-primary text-primary-foreground",
                  !isActive && !isDone && "border-border bg-background text-muted-foreground",
                )}
              >
                {isDone ? <Check className="h-3.5 w-3.5" /> : s.n}
              </span>
              <span
                className={cn(
                  "hidden text-sm md:inline",
                  isActive ? "font-semibold text-foreground" : "text-muted-foreground",
                )}
              >
                {s.label}
              </span>
            </div>
          );
          return (
            <li key={s.n} className="flex flex-1 items-center gap-2">
              {canGo ? (
                <Link to={s.path} className="hover:opacity-80">
                  {inner}
                </Link>
              ) : (
                <span className="cursor-not-allowed opacity-60">{inner}</span>
              )}
              {i < STEPS.length - 1 && (
                <span className={cn("h-px flex-1", isDone ? "bg-primary" : "bg-border")} />
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}