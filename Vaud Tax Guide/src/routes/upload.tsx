import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useCallback, useRef, useState } from "react";
import { useDropzone } from "react-dropzone";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { PageTransition } from "@/components/PageTransition";
import { Upload, FileText, X, Eye, EyeOff } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { extractDocument } from "@/lib/api";
import type { UploadedDoc } from "@/lib/types";

export const Route = createFileRoute("/upload")({
  head: () => ({ meta: [{ title: "Upload — VaudTaxAI" }] }),
  component: UploadPage,
});

function UploadPage() {
  const navigate = useNavigate();
  const documents = useAppStore((s) => s.documents);
  const addDocument = useAppStore((s) => s.addDocument);
  const updateDocument = useAppStore((s) => s.updateDocument);
  const removeDocument = useAppStore((s) => s.removeDocument);

  // Store file → object URL for in-browser PDF preview (not serializable, so kept in ref)
  const fileUrlsRef = useRef<Map<string, string>>(new Map());
  const [previewOpen, setPreviewOpen] = useState<Set<string>>(new Set());

  const togglePreview = (id: string) => {
    setPreviewOpen((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleFiles = useCallback(
    async (files: File[]) => {
      for (const file of files) {
        const id = crypto.randomUUID();
        const objectUrl = URL.createObjectURL(file);
        fileUrlsRef.current.set(id, objectUrl);
        const doc: UploadedDoc = {
          id,
          filename: file.name,
          status: "uploading",
          progress: 0,
          facts: [],
        };
        addDocument(doc);
        try {
          const res = await extractDocument(file, (pct) => {
            updateDocument(id, { progress: pct, status: pct < 100 ? "uploading" : "classifying" });
          });
          updateDocument(id, { status: "ready", progress: 100, facts: res.facts });
        } catch (err) {
          const msg = err instanceof Error ? err.message : "Upload failed";
          updateDocument(id, { status: "error", error: msg });
          toast.error(`${file.name}: ${msg}`);
        }
      }
    },
    [addDocument, updateDocument],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: { "application/pdf": [".pdf"] },
    multiple: true,
    onDrop: handleFiles,
  });

  const allReady = documents.length > 0 && documents.every((d) => d.status === "ready");

  return (
    <PageTransition>
      <header className="mb-8">
        <p className="text-sm font-medium uppercase tracking-widest text-primary">Step 2</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">Upload your documents</h1>
        <p className="mt-2 text-muted-foreground">
          Salary certificate, Pillar 3a statement, health insurance, bank statements — drop them all in.
        </p>
      </header>

      <div
        {...getRootProps()}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-12 text-center transition-colors ${
          isDragActive ? "border-primary bg-primary/5" : "border-border bg-card hover:border-primary/50"
        }`}
      >
        <input {...getInputProps()} />
        <Upload className="mb-3 h-8 w-8 text-muted-foreground" />
        <p className="text-base font-medium">
          {isDragActive ? "Drop the PDFs here" : "Drag PDFs here, or click to browse"}
        </p>
        <p className="mt-1 text-sm text-muted-foreground">PDF only · Multiple files supported</p>
      </div>

      {documents.length > 0 && (
        <ul className="mt-8 space-y-3">
          {documents.map((doc) => (
            <li key={doc.id} className="overflow-hidden rounded-lg border bg-card">
              <div className="flex items-center gap-3 p-4">
                <FileText className="h-4 w-4 text-muted-foreground" />
                <span className="flex-1 truncate text-sm font-medium">{doc.filename}</span>
                <StatusBadge doc={doc} />
                {doc.status === "ready" && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 gap-1 text-xs"
                    onClick={() => togglePreview(doc.id)}
                  >
                    {previewOpen.has(doc.id) ? (
                      <><EyeOff className="h-3.5 w-3.5" /> Hide</>
                    ) : (
                      <><Eye className="h-3.5 w-3.5" /> Preview</>
                    )}
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => {
                    const url = fileUrlsRef.current.get(doc.id);
                    if (url) URL.revokeObjectURL(url);
                    fileUrlsRef.current.delete(doc.id);
                    removeDocument(doc.id);
                  }}
                  aria-label="Remove"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
              {doc.status !== "ready" && doc.status !== "error" && (
                <div className="px-4 pb-4">
                  <Progress value={doc.progress} />
                </div>
              )}
              {doc.status === "error" && (
                <p className="px-4 pb-3 text-xs text-destructive">{doc.error}</p>
              )}
              {doc.status === "ready" && (
                <div className="px-4 pb-3 text-xs text-muted-foreground">
                  {doc.facts.length} fact{doc.facts.length === 1 ? "" : "s"} extracted
                </div>
              )}
              {doc.status === "ready" && previewOpen.has(doc.id) && (
                <div className="border-t">
                  <iframe
                    src={fileUrlsRef.current.get(doc.id) ?? ""}
                    title={`Preview of ${doc.filename}`}
                    className="h-96 w-full"
                  />
                </div>
              )}
            </li>
          ))}
        </ul>
      )}

      <div className="mt-10 flex justify-between">
        <Button asChild variant="ghost">
          <Link to="/intake">← Back</Link>
        </Button>
        <Button
          size="lg"
          disabled={!allReady}
          onClick={() => navigate({ to: "/review" })}
        >
          Review extracted facts
        </Button>
      </div>
    </PageTransition>
  );
}

function StatusBadge({ doc }: { doc: UploadedDoc }) {
  if (doc.status === "uploading")
    return <Badge variant="outline">Uploading {doc.progress}%</Badge>;
  if (doc.status === "classifying")
    return <Badge variant="outline" className="border-primary/40 text-primary">Classifying…</Badge>;
  if (doc.status === "ready")
    return <Badge className="bg-success text-success-foreground hover:bg-success/90">Ready</Badge>;
  return <Badge variant="destructive">Error</Badge>;
}