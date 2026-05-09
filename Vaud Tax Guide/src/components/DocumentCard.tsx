import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FileText } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { FactRow } from "./FactRow";
import type { UploadedDoc } from "@/lib/types";

export function DocumentCard({ doc }: { doc: UploadedDoc }) {
  const confirmAll = useAppStore((s) => s.confirmAllInDoc);
  const confirmedCount = doc.facts.filter((f) => f.confirmed_by_user).length;
  const allConfirmed = doc.facts.length > 0 && confirmedCount === doc.facts.length;

  return (
    <Accordion type="single" collapsible defaultValue={doc.id} className="rounded-lg border bg-card">
      <AccordionItem value={doc.id} className="border-0">
        <AccordionTrigger className="px-4 py-3 hover:no-underline">
          <div className="flex flex-1 items-center gap-3">
            <FileText className="h-4 w-4 text-muted-foreground" />
            <span className="truncate text-sm font-medium">{doc.filename}</span>
            <Badge
              variant="outline"
              className={
                allConfirmed
                  ? "border-success/40 bg-success/10 text-success"
                  : "border-amber-300 bg-amber-50 text-amber-800"
              }
            >
              {confirmedCount}/{doc.facts.length} confirmed
            </Badge>
          </div>
        </AccordionTrigger>
        <AccordionContent className="px-4 pb-4">
          {doc.facts.length === 0 ? (
            <p className="text-sm text-muted-foreground">No facts extracted from this document.</p>
          ) : (
            <>
              <div className="mb-3 flex justify-end">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => confirmAll(doc.id)}
                  disabled={allConfirmed}
                >
                  Confirm all
                </Button>
              </div>
              <div className="space-y-2">
                {doc.facts.map((f) => (
                  <FactRow key={f.canonical_field} docId={doc.id} fact={f} />
                ))}
              </div>
            </>
          )}
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}