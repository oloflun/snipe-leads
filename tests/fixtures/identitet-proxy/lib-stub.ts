// Stubbe för app/api/snajp-support/_lib.ts i lib/identitet-proxy.test.ts:
// backenden svarar 200 utan nät.
import { NextResponse } from "next/server";

export async function proxyWithApiKey() {
  return NextResponse.json({ ok: true }, { status: 200 });
}
