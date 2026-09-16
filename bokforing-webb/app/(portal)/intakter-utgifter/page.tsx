import { redirect } from "next/navigation";

/** Intäkter & utgifter hörde till bokföringsagenten. Kvitton är utlägg —
 *  listan och kategorisummorna bor under Kvitton respektive Översikt. */
export default function Page() {
  redirect("/kvitton");
}
