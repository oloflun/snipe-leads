"use client";

import { FelChatt } from "@/components/Felgrans";

/** Kundens publika chattlänk: ett fel här får inte bli Snajps felsida. */
export default function Error(
  props: Readonly<{ error: Error & { digest?: string }; reset: () => void }>
) {
  return <FelChatt {...props} />;
}
