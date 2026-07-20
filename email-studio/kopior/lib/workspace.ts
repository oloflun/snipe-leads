import { createClient } from "@/lib/supabase/server";
import type { BusinessContext, Profile, Workspace } from "@/lib/database.types";
import type { User } from "@supabase/supabase-js";

export type WorkspaceContext = {
  user: User;
  profile: Profile;
  workspace: Workspace;
  businessContext: BusinessContext | null;
};

export async function getProfileForUser(userId: string): Promise<Profile | null> {
  const supabase = await createClient();
  const { data, error } = await supabase
    .from("profiles")
    .select("*")
    .eq("id", userId)
    .maybeSingle();

  if (error) {
    throw new Error(error.message);
  }

  return data;
}

export async function getWorkspaceForUser(userId: string): Promise<Workspace | null> {
  const profile = await getProfileForUser(userId);
  if (!profile) {
    return null;
  }

  const supabase = await createClient();
  const { data, error } = await supabase
    .from("workspaces")
    .select("*")
    .eq("id", profile.workspace_id)
    .maybeSingle();

  if (error) {
    throw new Error(error.message);
  }

  return data;
}

export async function getBusinessContextForWorkspace(workspaceId: string): Promise<BusinessContext | null> {
  const supabase = await createClient();
  const { data, error } = await supabase
    .from("business_contexts")
    .select("*")
    .eq("workspace_id", workspaceId)
    .maybeSingle();

  if (error) {
    throw new Error(error.message);
  }

  return data;
}

export async function getWorkspaceContext(): Promise<WorkspaceContext | null> {
  const supabase = await createClient();
  const {
    data: { user }
  } = await supabase.auth.getUser();

  if (!user) {
    return null;
  }

  const profile = await getProfileForUser(user.id);
  if (!profile) {
    return null;
  }

  const workspace = await getWorkspaceForUser(user.id);
  if (!workspace) {
    return null;
  }

  const businessContext = await getBusinessContextForWorkspace(workspace.id);

  return {
    user,
    profile,
    workspace,
    businessContext
  };
}

export async function hasCompletedOnboarding(userId: string): Promise<boolean> {
  const profile = await getProfileForUser(userId);
  if (!profile) {
    return false;
  }

  const businessContext = await getBusinessContextForWorkspace(profile.workspace_id);
  return businessContext !== null;
}