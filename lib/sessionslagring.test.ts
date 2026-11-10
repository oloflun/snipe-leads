/**
 * Chattens sessionsidentitet. Kör: node --test "lib/*.test.ts"
 *
 * Kontraktet: `sessionsId` kastar aldrig. I en iframe med blockerad
 * tredjepartslagring kastar webbläsaren redan på `window.sessionStorage`, och
 * widgeten föll på det (Fas 0-fyndet H8, 2026-11-09).
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { sessionsId } from "./sessionslagring.ts";

type Fonster = { sessionStorage: Storage };
const globalt = globalThis as unknown as { window?: Fonster };

function medFonster<T>(fonster: Fonster, kor: () => T): T {
  const forut = globalt.window;
  globalt.window = fonster;
  try {
    return kor();
  } finally {
    globalt.window = forut;
  }
}

function minneslagring(): Storage {
  const data = new Map<string, string>();
  return {
    getItem: (k: string) => data.get(k) ?? null,
    setItem: (k: string, v: string) => void data.set(k, v),
    removeItem: (k: string) => void data.delete(k),
    clear: () => data.clear(),
    key: () => null,
    get length() {
      return data.size;
    }
  } as Storage;
}

test("samma nyckel ger samma id, och det sparas i sessionStorage", () => {
  const lagring = minneslagring();
  medFonster({ sessionStorage: lagring }, () => {
    const forsta = sessionsId("snajp.embed.session.prov");
    assert.match(forsta, /^[0-9a-f-]{20,}$/);
    assert.equal(sessionsId("snajp.embed.session.prov"), forsta);
    assert.equal(lagring.getItem("snajp.embed.session.prov"), forsta);
  });
});

test("blockerad lagring kastar inte, och id:t är stabilt så länge sidan lever", () => {
  const blockerat = {
    get sessionStorage(): Storage {
      throw new DOMException("The operation is insecure.", "SecurityError");
    }
  };
  medFonster(blockerat, () => {
    const forsta = sessionsId("snajp.embed.session.blockerad");
    assert.ok(forsta.length >= 20);
    assert.equal(sessionsId("snajp.embed.session.blockerad"), forsta);
    assert.notEqual(sessionsId("snajp.embed.session.annan"), forsta);
  });
});

test("lagring som kastar vid skrivning (full kvot) ger ändå ett stabilt id", () => {
  const full = {
    sessionStorage: {
      ...minneslagring(),
      getItem: () => null,
      setItem: () => {
        throw new DOMException("Quota exceeded.", "QuotaExceededError");
      }
    } as Storage
  };
  medFonster(full, () => {
    const forsta = sessionsId("snajp.demo.session.full");
    assert.equal(sessionsId("snajp.demo.session.full"), forsta);
  });
});
