"use client";

import { Felruta } from "@/components/Felruta";

/** Yttersta gränsen: inloggningen och allt utanför portalens skal. */
export default function Error(
  props: Readonly<{ error: Error & { digest?: string }; reset: () => void }>
) {
  return (
    <main className="min-h-dvh">
      <Felruta {...props} />
    </main>
  );
}
