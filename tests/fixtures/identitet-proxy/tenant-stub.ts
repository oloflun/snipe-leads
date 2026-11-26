// Stubbe för lib/snajp/tenant.ts i lib/identitet-proxy.test.ts. Testet styr
// utfallet genom globalThis.__identitetsprov.
type Prov = { tenantfel?: { status: number; kod: string }; roll?: string };

function prov(): Prov {
  return (globalThis as { __identitetsprov?: Prov }).__identitetsprov ?? {};
}

export class SnajpTenantError extends Error {
  status: number;
  kod: string;
  constructor(status: number, message: string, kod: string) {
    super(message);
    this.status = status;
    this.kod = kod;
  }
}

export function svarForTenantfel(error: SnajpTenantError) {
  return { error: error.message, kod: error.kod };
}

export async function requireSnajpTenant() {
  const { tenantfel, roll } = prov();
  if (tenantfel) {
    throw new SnajpTenantError(tenantfel.status, "fel", tenantfel.kod);
  }
  return {
    workspaceId: "w1",
    slug: "kund-a",
    apiKey: "nyckel",
    userId: "u1",
    isDemo: false,
    impersonerar: false,
    roll: roll ?? "owner"
  };
}

export async function snajpIdentitet() {
  return "identitet-u1";
}
