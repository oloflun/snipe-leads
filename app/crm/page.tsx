import { redirect } from "next/navigation";

/** CRM:et öppnar på bolagen: det är registret allt annat hänger på. */
export default function Page() {
  redirect("/crm/bolag");
}
