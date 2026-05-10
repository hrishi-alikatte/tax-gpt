import { createFileRoute, Link } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { PageTransition } from "@/components/PageTransition";
import { CitationText } from "@/components/CitationText";
import { buildCompletenessPayload, useAppStore } from "@/lib/store";
import { ragExplain } from "@/lib/api";
import { lookupCode, formatFactValue } from "@/lib/vaud-codes";
import { Copy, Send } from "lucide-react";
import type { ChatMessage } from "@/lib/types";

export const Route = createFileRoute("/copilot")({
  head: () => ({ meta: [{ title: "Copilot — VaudTaxAI" }] }),
  component: CopilotPage,
});

function CopilotPage() {
  const profile = useAppStore((s) => s.profile);
  const documents = useAppStore((s) => s.documents);
  const interview = useAppStore((s) => s.interview);
  const chatHistory = useAppStore((s) => s.chatHistory);
  const appendChat = useAppStore((s) => s.appendChat);
  const [question, setQuestion] = useState("");

  const payload = useMemo(
    () => buildCompletenessPayload({ profile, documents, interview } as never),
    [profile, documents, interview],
  );
  const facts = payload.confirmed_facts;

  const ask = useMutation({
    mutationFn: (q: string) => ragExplain({ question: q, profile, confirmed_facts: facts }),
    onSuccess: (res) => {
      const msg: ChatMessage = {
        role: "assistant",
        content: res.answer_en,
        citations: res.citations,
      };
      appendChat(msg);
    },
    onError: (err) => toast.error((err as Error).message),
  });

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const q = question.trim();
    if (!q) return;
    appendChat({ role: "user", content: q });
    ask.mutate(q);
    setQuestion("");
  };

  const summaryRows = useMemo(
    () =>
      facts.map((f) => {
        const c = lookupCode(f.canonical_field);
        return {
          code: c.code,
          label: c.label,
          group: c.group,
          value: formatFactValue(f.canonical_field, f.value),
        };
      }),
    [facts],
  );

  const copy = async () => {
    const text = summaryRows
      .map((r) => `${r.code}\t${r.label}\t${r.value}`)
      .join("\n");
    await navigator.clipboard.writeText(text);
    toast.success("Copied to clipboard");
  };

  return (
    <PageTransition>
      <header className="mb-8">
        <p className="text-sm font-medium uppercase tracking-widest text-primary">Step 6</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">Copilot & VaudTax summary</h1>
        <p className="mt-2 text-muted-foreground">
          Ask anything about your Vaud return — answers are grounded in the official 2025 instructions.
        </p>
      </header>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="flex h-[600px] flex-col rounded-lg border bg-card">
          <div className="border-b px-4 py-3">
            <h2 className="text-sm font-semibold">Source-grounded chat</h2>
          </div>
          <div className="flex-1 space-y-4 overflow-y-auto p-4">
            {chatHistory.length === 0 && (
              <div className="space-y-2 text-sm text-muted-foreground">
                <p>Try asking:</p>
                <ul className="list-disc pl-5">
                  <li>How do I deduct my commute from Lausanne to Renens?</li>
                  <li>Can I deduct Pillar 3a contributions in Vaud?</li>
                  <li>What's the maximum LPP buy-back deduction?</li>
                </ul>
              </div>
            )}
            {chatHistory.map((m, i) =>
              m.role === "user" ? (
                <div key={i} className="ml-auto max-w-[85%] rounded-lg bg-primary px-3 py-2 text-sm text-primary-foreground">
                  {m.content}
                </div>
              ) : (
                <div key={i} className="max-w-[90%] rounded-lg border bg-background p-3 text-sm">
                  <CitationText answer={m.content} citations={m.citations ?? []} />
                </div>
              ),
            )}
            {ask.isPending && <p className="text-xs text-muted-foreground">Thinking…</p>}
          </div>
          <form onSubmit={submit} className="flex gap-2 border-t p-3">
            <Input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask about your Vaud tax return…"
              disabled={ask.isPending}
            />
            <Button type="submit" disabled={ask.isPending || !question.trim()}>
              <Send className="h-4 w-4" />
            </Button>
          </form>
        </section>

        <section className="flex h-[600px] flex-col rounded-lg border bg-card">
          <div className="flex items-center justify-between border-b px-4 py-3">
            <h2 className="text-sm font-semibold">VaudTax codes summary</h2>
            <Button size="sm" variant="outline" onClick={copy} disabled={summaryRows.length === 0}>
              <Copy className="mr-2 h-3.5 w-3.5" /> Copy
            </Button>
          </div>
          <div className="flex-1 overflow-y-auto">
            {summaryRows.length === 0 ? (
              <p className="p-6 text-sm text-muted-foreground">
                No confirmed facts yet. Go back to the review step.
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-20">Code</TableHead>
                    <TableHead>Label</TableHead>
                    <TableHead className="text-right">Value</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {summaryRows.map((r, i) => (
                    <TableRow key={i}>
                      <TableCell className="font-mono text-xs">{r.code}</TableCell>
                      <TableCell className="text-sm">{r.label}</TableCell>
                      <TableCell className="text-right text-sm tabular-nums">{r.value}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        </section>
      </div>

      <div className="mt-10 flex justify-between">
        <Button asChild variant="ghost">
          <Link to="/dashboard">← Back to dashboard</Link>
        </Button>
      </div>
    </PageTransition>
  );
}
