import { redirect } from "next/navigation";

/** Gamla dokumentfliken — kvittolistan är dess efterträdare. */
export default function Page() {
  redirect("/kvitton");
}
