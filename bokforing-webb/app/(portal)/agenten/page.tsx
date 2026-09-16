import { redirect } from "next/navigation";

/** Gamla uppladdningsfliken. Kvittohanteraren skannar inkorgen — och
 *  uppladdningen bor numera under Kvitton. Bokmärken ska landa rätt. */
export default function Page() {
  redirect("/inkorgen");
}
