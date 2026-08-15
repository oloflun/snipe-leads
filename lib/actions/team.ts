"use server";

import { revalidatePath } from "next/cache";
import { createAdminClient } from "@/lib/supabase/admin";
import { getWorkspaceContext } from "@/lib/workspace";

export type TeamActionResult = {
  success: boolean;
  error?: string;
  message?: string;
};

export type TeamMember = {
  id: string;
  /**
   * För en medlem är det `profiles.full_name`, för en inbjudan adressen.
   * `profiles` har ingen e-postkolumn — adressen bor i `auth.users` och läses
   * inte hit, eftersom teamlistan inte är ett skäl att kopiera identiteter ut
   * ur auth-schemat.
   */
  label: string;
  role: string;
  status: "member" | "invited";
};

const ROLES = ["owner", "member"] as const;
type Role = (typeof ROLES)[number];

/**
 * `workspace_invites` har haft tabell och läspolicy sedan 006, men ingen
 * skrivväg i appen — TeamSettings visade fyra hårdkodade strängar. Triggern
 * `on_auth_user_created` läser tabellen och lägger användaren i rätt workspace
 * oavsett inloggningssätt, så en rad här är allt som krävs för att en
 * inbjudan ska fungera.
 *
 * Går via service-rollen med flit: RLS på tabellen har SELECT-policy men inga
 * skrivpolicyer, vilket är rätt — en klient ska aldrig kunna skriva en
 * inbjudan direkt, eftersom `workspace_id` då hade kommit från klienten.
 * Här kommer det ur sessionen.
 */
export async function inviteMember(email: string, role: string): Promise<TeamActionResult> {
  const normalized = email.trim().toLowerCase();
  if (!normalized.includes("@")) {
    return { success: false, error: "Skriv en giltig e-postadress." };
  }
  if (!ROLES.includes(role as Role)) {
    return { success: false, error: "Okänd roll." };
  }

  const context = await getWorkspaceContext();
  if (!context) {
    return { success: false, error: "Du måste vara inloggad." };
  }

  // Bara den som äger arbetsytan får bjuda in. Utan den här raden hade varje
  // medlem kunnat lägga till en ny medlem, och därmed kunnat ge sig själv en
  // andra ingång som överlever att det egna kontot stängs av.
  if (context.profile.role !== "owner") {
    return { success: false, error: "Bara arbetsytans ägare kan bjuda in nya medlemmar." };
  }

  const admin = createAdminClient();
  const { error } = await admin.from("workspace_invites").insert({
    email: normalized,
    workspace_id: context.workspace.id,
    role,
    invited_by: context.user.id
  });

  if (error) {
    // Det delvis unika indexet workspace_invites_open_key tillåter en obrukad
    // inbjudan per adress och workspace. En kollision är alltså inte ett fel
    // utan ett tillstånd användaren ska få veta om.
    if (error.code === "23505") {
      return {
        success: false,
        error: `${normalized} har redan en inbjudan som väntar.`
      };
    }
    return { success: false, error: error.message };
  }

  revalidatePath("/settings/team");
  return {
    success: true,
    message: `${normalized} läggs till i arbetsytan nästa gång de loggar in. Skicka länken till dem — vi mejlar inte inbjudan automatiskt än.`
  };
}

/**
 * Medlemmar plus obrukade inbjudningar, i en lista.
 *
 * Två källor eftersom det är två tillstånd: en rad i `profiles` är någon som
 * varit här, en rad i `workspace_invites` är någon som förväntas. Att visa
 * bara det första hade gjort en skickad inbjudan osynlig, vilket är precis när
 * någon skickar den en gång till.
 */
export async function listTeam(): Promise<TeamMember[]> {
  const context = await getWorkspaceContext();
  if (!context) {
    return [];
  }

  const admin = createAdminClient();

  const [{ data: profiles }, { data: invites }] = await Promise.all([
    admin
      .from("profiles")
      .select("id, full_name, role")
      .eq("workspace_id", context.workspace.id),
    admin
      .from("workspace_invites")
      .select("id, email, role")
      .eq("workspace_id", context.workspace.id)
      .is("accepted_at", null)
  ]);

  const members: TeamMember[] = (profiles ?? []).map((row) => ({
    id: row.id as string,
    label: (row.full_name as string) || "Namnlös medlem",
    role: (row.role as string) ?? "member",
    status: "member"
  }));

  const pending: TeamMember[] = (invites ?? []).map((row) => ({
    id: row.id as string,
    label: row.email as string,
    role: (row.role as string) ?? "member",
    status: "invited"
  }));

  return [...members, ...pending];
}

export async function revokeInvite(inviteId: string): Promise<TeamActionResult> {
  const context = await getWorkspaceContext();
  if (!context) {
    return { success: false, error: "Du måste vara inloggad." };
  }
  if (context.profile.role !== "owner") {
    return { success: false, error: "Bara arbetsytans ägare kan ta bort inbjudningar." };
  }

  const admin = createAdminClient();
  // workspace_id i where-satsen är inte överflödig: utan den hade ett id från
  // en annan arbetsyta gått att radera härifrån, eftersom service-rollen inte
  // begränsas av RLS.
  const { error } = await admin
    .from("workspace_invites")
    .delete()
    .eq("id", inviteId)
    .eq("workspace_id", context.workspace.id)
    .is("accepted_at", null);

  if (error) {
    return { success: false, error: error.message };
  }

  revalidatePath("/settings/team");
  return { success: true, message: "Inbjudan borttagen." };
}
