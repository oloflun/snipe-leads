"use client";

import { FelArbetsyta } from "@/components/Felgrans";

/** Ett fel i en vy stannar i vyn: menyn står kvar — se components/Felgrans.tsx. */
export default function Error(
  props: Readonly<{ error: Error & { digest?: string }; reset: () => void }>
) {
  return <FelArbetsyta {...props} />;
}
