/**
 * En person som API:t svarar med den (`person_ut` i snajp-support/app/api/crm_v1.py).
 * `Person` i api.ts bär listans fält; posten har dessutom rättslig grund,
 * externa id:n och tiderna, som panelen visar.
 */
import type { Person } from "@/lib/crm/api";
import type { Localized } from "@/lib/i18n";

export type RattsligGrund = "contract" | "legitimate_interest" | "consent";

export type Personpost = Person & {
  legal_basis?: RattsligGrund | null;
  external_ids?: { connection: string; id: string; last_seen_at: string | null }[];
  created_at?: string | null;
  deleted_at?: string | null;
};

/** GDPR artikel 6, som API:t skriver grunden. */
export const GRUNDER: Record<RattsligGrund, Localized> = {
  contract: { sv: "Avtal", en: "Contract" },
  legitimate_interest: { sv: "Berättigat intresse", en: "Legitimate interest" },
  consent: { sv: "Samtycke", en: "Consent" }
};

/** "Per Påhitt", annars e-postadressen, annars inget. */
export function personnamn(p: Pick<Person, "first_name" | "last_name" | "email">): string | null {
  return [p.first_name, p.last_name].filter(Boolean).join(" ") || p.email || null;
}
