import { useState } from "react";
import { Check, Pencil } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import { formatFactValue, lookupCode } from "@/lib/vaud-codes";
import type { TaxFact } from "@/lib/types";

export function FactRow({ docId, fact }: { docId: string; fact: TaxFact }) {
  const toggle = useAppStore((s) => s.toggleFactConfirm);
  const edit = useAppStore((s) => s.editFact);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(String(fact.value));
  const code = lookupCode(fact.canonical_field);
  const conf = Math.round((fact.confidence ?? 0) * 100);

  const save = () => {
    const num = Number(draft);
    const next: TaxFact["value"] = !Number.isNaN(num) && draft.trim() !== "" ? num : draft;
    edit(docId, fact.canonical_field, next);
    setEditing(false);
  };

  return (
    <div
      className={cn(
        "flex flex-col gap-2 rounded-md border p-3 sm:flex-row sm:items-center sm:gap-4",
        fact.confirmed_by_user ? "border-success/40 bg-success/5" : "border-border bg-background",
      )}
    >
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] font-medium text-muted-foreground">
            {code.code}
          </span>
          <span className="truncate text-sm font-medium">{code.label}</span>
          <TooltipProvider delayDuration={100}>
            <Tooltip>
              <TooltipTrigger asChild>
                <span
                  className={cn(
                    "rounded px-1.5 py-0.5 text-[10px] font-medium tabular-nums",
                    conf >= 90 ? "bg-success/15 text-success" : conf >= 70 ? "bg-amber-100 text-amber-800" : "bg-destructive/10 text-destructive",
                  )}
                >
                  {conf}%
                </span>
              </TooltipTrigger>
              <TooltipContent>Extraction confidence</TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
        <p className="mt-1 truncate text-xs text-muted-foreground">{fact.canonical_field}</p>
      </div>
      <div className="flex items-center gap-2 sm:w-72">
        {editing ? (
          <Input
            autoFocus
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && save()}
            className="h-8"
          />
        ) : (
          <span className="flex-1 text-right text-sm tabular-nums">
            {formatFactValue(fact.canonical_field, fact.value)}
          </span>
        )}
        {editing ? (
          <Button size="sm" onClick={save}>Save</Button>
        ) : (
          <>
            <Button
              size="icon"
              variant="ghost"
              onClick={() => setEditing(true)}
              aria-label="Correct"
            >
              <Pencil className="h-3.5 w-3.5" />
            </Button>
            <Button
              size="sm"
              variant={fact.confirmed_by_user ? "default" : "outline"}
              onClick={() => toggle(docId, fact.canonical_field)}
              className="gap-1"
            >
              <Check className="h-3.5 w-3.5" />
              {fact.confirmed_by_user ? "Confirmed" : "Confirm"}
            </Button>
          </>
        )}
      </div>
    </div>
  );
}