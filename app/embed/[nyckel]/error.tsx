"use client";

import { FelChatt } from "@/components/Felgrans";

/** Widgeten visas på kundens sajt: ett fel här får inte bli Snajps felsida. */
export default function Error(
  props: Readonly<{ error: Error & { digest?: string }; reset: () => void }>
) {
  return <FelChatt {...props} />;
}
