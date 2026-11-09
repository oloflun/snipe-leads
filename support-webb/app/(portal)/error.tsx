"use client";

import { Felruta } from "@/components/Felruta";

/** Ett fel i en vy stannar i vyn: sidomenyn i layout.tsx står kvar. */
export default function Error(
  props: Readonly<{ error: Error & { digest?: string }; reset: () => void }>
) {
  return <Felruta {...props} />;
}
