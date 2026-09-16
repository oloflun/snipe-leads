import { redirect } from "next/navigation";

/**
 * Gamla produktadressen. Bokföringsagenten byggdes om till Kvittohanteraren
 * 2026-09-16 och marknadssidan bor på /kvitton — länkar och bokmärken hit
 * ska landa där, inte i en 404.
 */
export default function Page() {
  redirect("/kvitton");
}
