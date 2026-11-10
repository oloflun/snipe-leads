"use client";

import { FelHelsida } from "@/components/Felgrans";

/** Egen gräns, så att "Försök igen" renderar om onboardingen och inte hela appen. */
export default function Error(
  props: Readonly<{ error: Error & { digest?: string }; reset: () => void }>
) {
  return <FelHelsida {...props} />;
}
