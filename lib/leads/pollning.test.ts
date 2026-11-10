/**
 * Pollning som tål en störning. Kör: node --test "lib/**\/*.test.ts"
 *
 * Före (Fas 0, 2026-11-09): en enda misslyckad hämtning (ett nätavbrott på en
 * sekund, ett 502 under en deploy) avbröt förloppsvisningen för en körning som
 * fortsatte på servern. Användaren såg ett fel och inget förlopp.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { taligHamtning } from "./pollning.ts";

function skakig(utfall: Array<"ok" | "fel">) {
  let anrop = 0;
  return {
    hamta: async () => {
      const u = utfall[Math.min(anrop, utfall.length - 1)];
      anrop += 1;
      if (u === "fel") throw new Error(`fel ${anrop}`);
      return { nr: anrop };
    },
    antal: () => anrop
  };
}

test("en lyckad hämtning ger sitt värde", async () => {
  const hamta = taligHamtning(skakig(["ok"]).hamta);
  assert.deepEqual(await hamta(), { nr: 1 });
});

test("ett enstaka fel ger null i stället för att kasta", async () => {
  const hamta = taligHamtning(skakig(["fel", "ok"]).hamta);
  assert.equal(await hamta(), null);
  assert.deepEqual(await hamta(), { nr: 2 });
});

test("ihållande fel kastar det sista felet när taket är nått", async () => {
  const hamta = taligHamtning(skakig(["fel"]).hamta, 3);
  assert.equal(await hamta(), null);
  assert.equal(await hamta(), null);
  await assert.rejects(hamta(), /fel 3/);
});

test("en lyckad hämtning nollställer räkningen", async () => {
  const hamta = taligHamtning(skakig(["fel", "fel", "ok", "fel", "fel", "ok"]).hamta, 3);
  assert.equal(await hamta(), null);
  assert.equal(await hamta(), null);
  assert.deepEqual(await hamta(), { nr: 3 });
  assert.equal(await hamta(), null);
  assert.equal(await hamta(), null);
  assert.deepEqual(await hamta(), { nr: 6 });
});
