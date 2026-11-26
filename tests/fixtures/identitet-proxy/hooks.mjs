// Upplösning för lib/identitet-proxy.test.ts: låter node --test ladda
// app/api/snajp-support/_auth.ts utan Next. `@/`-aliaset pekar på repot,
// tenant-modulen och backendproxyn byts mot stubbar (ingen databas, inget nät),
// och next/server får sin filändelse.
import { pathToFileURL } from "node:url";
import { resolve as losUpp } from "node:path";

const ROT = losUpp(import.meta.dirname, "..", "..", "..");
const HAR = import.meta.dirname;

export async function resolve(specifier, context, nextResolve) {
  if (specifier === "@/lib/snajp/tenant") {
    return { url: pathToFileURL(losUpp(HAR, "tenant-stub.ts")).href, shortCircuit: true };
  }
  if (specifier === "./_lib" && context.parentURL?.endsWith("/_auth.ts")) {
    return { url: pathToFileURL(losUpp(HAR, "lib-stub.ts")).href, shortCircuit: true };
  }
  if (specifier.startsWith("@/")) {
    return { url: pathToFileURL(losUpp(ROT, `${specifier.slice(2)}.ts`)).href, shortCircuit: true };
  }
  if (specifier === "next/server") {
    return nextResolve("next/server.js", context);
  }
  return nextResolve(specifier, context);
}
