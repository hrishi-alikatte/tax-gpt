# Fix the blank "This page didn't load" error

## Diagnosis

The SSR log shows: `Cannot find module '@/components/HydrateStore' imported from '/dev-server/src/routes/__root.tsx'`.

Inspecting disk reveals the previous turn's two batched `apply_patch` calls only wrote the **first file** in each batch and silently dropped the rest. Currently on disk:

- `src/components/`: only `HydrateStore.tsx`, `PageTransition.tsx`, `Stepper.tsx`
- `src/routes/`: only `__root.tsx`, `index.tsx`, `upload.tsx`

Missing (but referenced by `__root.tsx`, `upload.tsx`, and other expected routes):

- `src/components/CitationText.tsx`
- `src/components/FactRow.tsx`
- `src/components/DocumentCard.tsx`
- `src/routes/intake.tsx`
- `src/routes/review.tsx`
- `src/routes/interview.tsx`
- `src/routes/dashboard.tsx`
- `src/routes/copilot.tsx`

(The reason `tsc --noEmit` returned clean was that the missing routes weren't reachable from the type-check graph, so missing imports went unnoticed.)

The `HydrateStore` resolution failure is a real, cold module — not a Vite cache issue. Vite is failing on the very first import in `__root.tsx` because that whole import chain explodes the moment it tries to load a route file that itself imports a missing component.

## Fix

Re-create the 8 missing files using the exact contents from the previous turn (already designed and reviewed):

1. `src/components/CitationText.tsx` — RAG markdown renderer with citation badge replacement.
2. `src/components/FactRow.tsx` — single fact row with confirm/correct controls.
3. `src/components/DocumentCard.tsx` — accordion item per uploaded document.
4. `src/routes/intake.tsx` — Screen 1.
5. `src/routes/review.tsx` — Screen 3.
6. `src/routes/interview.tsx` — Screen 4.
7. `src/routes/dashboard.tsx` — Screen 5.
8. `src/routes/copilot.tsx` — Screen 6.

Each file will be added in its **own** `apply_patch` call to avoid the silent-truncation issue that bit the previous batch.

After re-creating the files, run `bunx tsc --noEmit` for a real verification that all import edges resolve, then check the preview console for any runtime errors.

No design or behavior changes — this is purely restoring files that were lost during patch application.
