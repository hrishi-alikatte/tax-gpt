import { useEffect, useState, type ReactNode } from "react";
import { useAppStore } from "@/lib/store";

export function HydrateStore({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  useEffect(() => {
    Promise.resolve(useAppStore.persist.rehydrate()).finally(() => setReady(true));
  }, []);
  return ready ? <>{children}</> : null;
}