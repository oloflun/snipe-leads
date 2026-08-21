import "server-only";

import { cache } from "react";
import { auth } from "@/lib/auth";
import { hasDatabase, sqlAsUser } from "@/lib/db";
import type { BusinessContext, Profile, Workspace } from "@/lib/database.types";

export type WorkspaceUser = { id: string; email: string | null; name: string | null };

export type WorkspaceContext = {
  user: WorkspaceUser;
  profile: Profile;
  workspace: Workspace;
  businessContext: BusinessContext | null;
};

export async function getProfileForUser(userId: string): Promise<Profile | null> {
  const rows = await sqlAsUser<Profile>(userId, "select * from public.profiles where id = $1", [
    userId
  ]);
  return rows[0] ?? null;
}

export async function getWorkspaceForUser(userId: string): Promise<Workspace | null> {
  const rows = await sqlAsUser<Workspace>(
    userId,
    `select w.* from public.workspaces w
       join public.profiles p on p.workspace_id = w.id
      where p.id = $1`,
    [userId]
  );
  return rows[0] ?? null;
}

export async function getBusinessContextForWorkspace(
  workspaceId: string,
  userId: string
): Promise<BusinessContext | null> {
  const rows = await sqlAsUser<BusinessContext>(
    userId,
    "select * from public.business_contexts where workspace_id = $1",
    [workspaceId]
  );
  return rows[0] ?? null;
}

/**
 * Avdupliceras per request med React `cache`. Utan den ställer en enda sidladdning
 * frågan fyra gånger: layouten, `resolveDashboardState`, `getPlatformAdmin` och
 * `aktivVy` behöver alla samma svar, och sessionen kan inte ändras mitt i ett
 * request. Fyra identiska rundturer till databasen är inte fel svar, bara
 * betalda tre gånger om.
 */
export const getWorkspaceContext = cache(async function getWorkspaceContext(): Promise<WorkspaceContext | null> {
  // Utan databas finns per definition ingen inloggad användare. Att returnera
  // null låter varje anropare falla tillbaka på sin anonyma väg; att kasta här
  // tog förut ner publika sidor som aldrig behövde en session.
  if (!hasDatabase()) {
    return null;
  }

  const session = await auth();
  const userId = session?.user?.id;
  if (!userId) {
    return null;
  }

  // Fyra PostgREST-anrop och fyra klienter per anrop blev en fråga. Samma svar,
  // en tur och retur — och samma RLS, eftersom app.user_id sätts i
  // transaktionen.
  const rows = await sqlAsUser<{
    profile: Profile;
    workspace: Workspace;
    business_context: BusinessContext | null;
  }>(
    userId,
    `select to_jsonb(p.*)  as profile,
            to_jsonb(w.*)  as workspace,
            to_jsonb(bc.*) as business_context
       from public.profiles p
       join public.workspaces w on w.id = p.workspace_id
       left join public.business_contexts bc on bc.workspace_id = w.id
      where p.id = $1
      limit 1`,
    [userId]
  );

  const row = rows[0];
  if (!row?.profile || !row?.workspace) {
    return null;
  }

  return {
    user: {
      id: userId,
      email: session.user.email ?? null,
      name: session.user.name ?? null
    },
    profile: row.profile,
    workspace: row.workspace,
    businessContext: row.business_context ?? null
  };
});

export async function hasCompletedOnboarding(userId: string): Promise<boolean> {
  const rows = await sqlAsUser<{ ok: boolean }>(
    userId,
    `select (bc.id is not null) as ok
       from public.profiles p
       left join public.business_contexts bc on bc.workspace_id = p.workspace_id
      where p.id = $1
      limit 1`,
    [userId]
  );
  return Boolean(rows[0]?.ok);
}
