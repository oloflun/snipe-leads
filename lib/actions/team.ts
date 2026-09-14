"use server";

import { revalidatePath } from "next/cache";
import { sqlAsUser } from "@/lib/db";
import { aktivVy } from "@/lib/vy";
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
 * Gick förut via service-rollen, alltså en anslutning utan radsäkerhet, för att
 * tabellen saknade skrivpolicyer. Nu finns de (032): `workspace_id` måste vara
 * anroparens egen och bara ägaren släpps igenom, kontrollerat av databasen.
 * Ägarkontrollen nedan står kvar ändå — den ger ett begripligt svenskt
 * felmeddelande i stället för ett nakent policyavslag.
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

  // Demo OCH kundbesök: arbetsytan bakom vyn är fortfarande adminens EGEN
  // (samma fälla som affärskontexten/betalsätt/plan hade). Utan den här
  // spärren bjuder "bjud in" under ett kundbesök in någon till SNAJPS eget
  // team, inte kundens.
  if ((await aktivVy()).vy !== "admin") {
    return { success: false, error: "Går inte att bjuda in i demo- eller kundvy." };
  }

  // Bara den som äger arbetsytan får bjuda in. Utan den här raden hade varje
  // medlem kunnat lägga till en ny medlem, och därmed kunnat ge sig själv en
  // andra ingång som överlever att det egna kontot stängs av.
  if (context.profile.role !== "owner") {
    return { success: false, error: "Bara arbetsytans ägare kan bjuda in nya medlemmar." };
  }

  try {
    await sqlAsUser(
      context.user.id,
      `insert into public.workspace_invites (email, workspace_id, role, invited_by)
       values ($1, $2, $3, $4)`,
      [normalized, context.workspace.id, role, context.user.id]
    );
  } catch (error) {
    // Det delvis unika indexet workspace_invites_open_key tillåter en obrukad
    // inbjudan per adress och workspace. En kollision är alltså inte ett fel
    // utan ett tillstånd användaren ska få veta om.
    if ((error as { code?: string }).code === "23505") {
      return {
        success: false,
        error: `${normalized} har redan en inbjudan som väntar.`
      };
    }
    return { success: false, error: (error as Error).message };
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

  // Samma fälla: en lista härifrån under ett kundbesök vore SNAJPS eget team
  // visat som om det tillhörde kunden.
  if ((await aktivVy()).vy !== "admin") {
    return [];
  }

  // Två frågor blev en union: samma två tillstånd, ett tur och retur, och
  // ordningen (medlemmar först) blir databasens jobb i stället för en
  // konkatenering som råkar hamna rätt.
  const rows = await sqlAsUser<{
    id: string;
    label: string;
    role: string;
    status: "member" | "invited";
  }>(
    context.user.id,
    `select id, coalesce(nullif(full_name, ''), 'Namnlös medlem') as label,
            coalesce(role, 'member') as role, 'member' as status, 0 as sort
       from public.profiles where workspace_id = $1
     union all
     select id, email as label, coalesce(role, 'member') as role, 'invited' as status, 1 as sort
       from public.workspace_invites
      where workspace_id = $1 and accepted_at is null
     order by sort, label`,
    [context.workspace.id]
  );

  return rows.map(({ id, label, role, status }) => ({ id, label, role, status }));
}

export async function revokeInvite(inviteId: string): Promise<TeamActionResult> {
  const context = await getWorkspaceContext();
  if (!context) {
    return { success: false, error: "Du måste vara inloggad." };
  }
  if ((await aktivVy()).vy !== "admin") {
    return { success: false, error: "Går inte att ändra i demo- eller kundvy." };
  }
  if (context.profile.role !== "owner") {
    return { success: false, error: "Bara arbetsytans ägare kan ta bort inbjudningar." };
  }

  // workspace_id och accepted_at står kvar i where-satsen trots att policyn
  // (032) nu kräver båda. Dubbelt, med flit: villkoret i policyn är grinden,
  // villkoret här är det som gör avsikten läsbar på anropsstället.
  try {
    await sqlAsUser(
      context.user.id,
      `delete from public.workspace_invites
        where id = $1 and workspace_id = $2 and accepted_at is null`,
      [inviteId, context.workspace.id]
    );
  } catch (error) {
    return { success: false, error: (error as Error).message };
  }

  revalidatePath("/settings/team");
  return { success: true, message: "Inbjudan borttagen." };
}
