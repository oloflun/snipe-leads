/**
 * Läser en hemlighet åt QA-skripten: först miljövariabeln, sedan `.env.deploy`
 * i repots rot (gitignorerad). Värdet skrivs aldrig ut.
 *
 * Finns för att plattformsadminens lösenord stod som reservvärde i tre
 * incheckade skript (Fas 0-fyndet K1, 2026-11-09). Ett lösenord i koden är ett
 * lösenord i varje klon och i hela historiken; ett skript som saknar det ska
 * stanna och säga var det hör hemma, inte bära med sig det.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ENV_DEPLOY = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", ".env.deploy");

export function hemlighet(namn) {
  const urMiljon = process.env[namn];
  if (urMiljon) return urMiljon;
  let text = "";
  try {
    text = fs.readFileSync(ENV_DEPLOY, "utf8");
  } catch {
    // Filen saknas i en ren klon; felet nedan säger vad som behövs.
  }
  for (const rad of text.split(/\r?\n/)) {
    const m = rad.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)$/);
    if (m && m[1] === namn) {
      const varde = m[2].trim().replace(/^(["'])(.*)\1$/, "$2");
      if (varde) return varde;
    }
  }
  console.error(
    `${namn} saknas. Sätt miljövariabeln eller lägg raden ${namn}=... i .env.deploy (${ENV_DEPLOY}).`,
  );
  process.exit(2);
}
