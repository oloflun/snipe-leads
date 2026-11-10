"use client";

import { FelAdmin } from "@/components/Felgrans";

/** Ett fel i en adminvy stannar i vyn: skalet i layout.tsx står kvar. */
export default function Error(
  props: Readonly<{ error: Error & { digest?: string }; reset: () => void }>
) {
  return <FelAdmin {...props} />;
}
