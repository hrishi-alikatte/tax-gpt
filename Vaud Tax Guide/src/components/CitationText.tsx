import ReactMarkdown from "react-markdown";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import type { RagCitation } from "@/lib/types";

const TOKEN_RE = /\[Vaud 2025 Instructions p\.\d+\]/g;

function renderWithCitations(text: string, citations: RagCitation[]) {
  const map = new Map(citations.map((c) => [c.token, c]));
  const parts: Array<string | { token: string; cite?: RagCitation }> = [];
  let last = 0;
  for (const m of text.matchAll(TOKEN_RE)) {
    const idx = m.index ?? 0;
    if (idx > last) parts.push(text.slice(last, idx));
    parts.push({ token: m[0], cite: map.get(m[0]) });
    last = idx + m[0].length;
  }
  if (last < text.length) parts.push(text.slice(last));

  return parts.map((p, i) => {
    if (typeof p === "string") return <span key={i}>{p}</span>;
    const title = p.cite?.section_title ?? "Vaud 2025 Instructions";
    const page = p.cite?.page;
    return (
      <TooltipProvider key={i} delayDuration={100}>
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              type="button"
              className="mx-0.5 inline-flex items-center rounded-md border border-primary/30 bg-primary/5 px-1.5 py-0.5 align-baseline text-xs font-medium text-primary transition-colors hover:bg-primary/10"
            >
              {page ? `p.${page}` : "ref"}
            </button>
          </TooltipTrigger>
          <TooltipContent side="top">
            <span className="text-xs font-medium">{title}</span>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  });
}

export function CitationText({
  answer,
  citations,
}: {
  answer: string;
  citations: RagCitation[];
}) {
  return (
    <div className="prose prose-sm max-w-none text-foreground prose-p:my-2 prose-strong:text-foreground prose-li:my-1">
      <ReactMarkdown
        components={{
          p: ({ children }) => <p>{flattenCitations(children, citations)}</p>,
          li: ({ children }) => <li>{flattenCitations(children, citations)}</li>,
        }}
      >
        {answer}
      </ReactMarkdown>
    </div>
  );
}

function flattenCitations(children: React.ReactNode, citations: RagCitation[]): React.ReactNode {
  return Array.isArray(children)
    ? children.map((c, i) =>
        typeof c === "string" ? <span key={i}>{renderWithCitations(c, citations)}</span> : c,
      )
    : typeof children === "string"
      ? renderWithCitations(children, citations)
      : children;
}