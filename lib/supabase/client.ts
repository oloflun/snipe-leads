"use client";

import { createBrowserClient } from "@supabase/ssr";
import { getBrowserSupabaseKey, getSupabaseUrl } from "@/lib/supabase/env";

export function createClient() {
  return createBrowserClient(getSupabaseUrl(), getBrowserSupabaseKey());
}