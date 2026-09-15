import { redirect } from "next/navigation";

/**
 * Bokföringens användningsvy bor sedan 2026-09-15 i den samlade
 * /admin/agentanvandning (alla tre agenterna på en sida). Routen står kvar
 * som omdirigering: bokmärken och gamla länkar ska landa rätt, inte i 404.
 */
export default function Page() {
  redirect("/admin/agentanvandning");
}
