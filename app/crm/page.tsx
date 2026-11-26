import { redirect } from "next/navigation";

/** CRM:et öppnar på översikten: registret, kunderna och synken i en blick. */
export default function Page() {
  redirect("/crm/oversikt");
}
