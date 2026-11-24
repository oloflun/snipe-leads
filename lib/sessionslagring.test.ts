/**
 * Chattens sessionsidentitet. Kör: node --test "lib/*.test.ts"
 *
 * Kontraktet: `sessionsId` kastar aldrig. I en iframe med blockerad
 * tredjepartslagring kastar webbläsaren redan på `window.sessionStorage`, och
 * widgeten föll på det (Fas 0-fyndet H8, 2026-11-09).
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { harSessionsId, sessionsId } from "./sessionslagring.ts";

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

test("utan randomUUID (osäker kontext) kommer id:t ändå ur kryptografisk slump, inte Math.random", () => {
  // Id:t läser tillbaka samtalet, så det får inte gå att gissa.
  const mathRandom = Math.random;
  Object.defineProperty(crypto, "randomUUID", {
    configurable: true,
    value: () => {
      throw new TypeError("randomUUID kräver säker kontext");
    }
  });
  Math.random = () => 0.5;
  try {
    medFonster({ sessionStorage: minneslagring() }, () => {
      const forsta = sessionsId("snajp.demo.session.osaker.1");
      const andra = sessionsId("snajp.demo.session.osaker.2");
      assert.match(forsta, /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/);
      assert.notEqual(forsta, andra);
    });
  } finally {
    // Egenskapen lades på instansen; den riktiga sitter kvar på prototypen.
    delete (crypto as unknown as { randomUUID?: unknown }).randomUUID;
    Math.random = mathRandom;
  }
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

test("harSessionsId skapar ingen identitet, och ser en som finns", () => {
  const lagring = minneslagring();
  medFonster({ sessionStorage: lagring }, () => {
    // En ny besökare har ingen: då finns inget samtal att hämta, och frågan
    // till backenden ska inte gå (SupportChat, hämtningen vid sidladdning).
    assert.equal(harSessionsId("snajp.demo.session.prov"), false);
    assert.equal(lagring.getItem("snajp.demo.session.prov"), null);
    const id = sessionsId("snajp.demo.session.prov");
    assert.equal(harSessionsId("snajp.demo.session.prov"), true);
    assert.equal(sessionsId("snajp.demo.session.prov"), id);
  });
});

test("harSessionsId kastar inte när lagringen är blockerad", () => {
  const blockerad = {
    get sessionStorage(): Storage {
      throw new DOMException("blockerad", "SecurityError");
    }
  } as Fonster;
  medFonster(blockerad, () => {
    assert.equal(harSessionsId("snajp.demo.session.blockerad"), false);
    sessionsId("snajp.demo.session.blockerad");
    assert.equal(harSessionsId("snajp.demo.session.blockerad"), true);
  });
});
