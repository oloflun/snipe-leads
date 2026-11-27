/**
 * En uppgift som API:t lämnar den (`uppgift_ut` i crm_v1_objekt.py). En uppgift
 * kan stå för sig själv eller höra till ett bolag, en person och en affär.
 */
export type Uppgiftsstatus = "todo" | "in_progress" | "done";

export type Uppgift = {
  id: string;
  title: string | null;
  description: string | null;
  status: Uppgiftsstatus;
  due_at: string | null;
  completed_at: string | null;
  owner: string | null;
  company_id: string | null;
  person_id: string | null;
  deal_id: string | null;
  created_at: string | null;
  updated_at: string | null;
  deleted_at?: string | null;
};

/** Tidpunkten som en lokal dag, `ÅÅÅÅ-MM-DD`. */
export function lokalDag(v: string): string {
  const d = new Date(v);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** Dagen som en tidpunkt klockan nio lokal tid, som uppgifter sparas från appen. */
export const dagSomTid = (dag: string): string => new Date(`${dag}T09:00:00`).toISOString();
