/**
 * En hämtning som tål en störning, för slingor som följer ett jobb.
 *
 * Arbetet fortsätter på servern oavsett vad webbläsaren ser. En enda
 * misslyckad hämtning (ett nätavbrott, ett 502 under en deploy) ska därför
 * inte avbryta förloppsvisningen: slingan hoppar över varvet och frågar igen.
 * Först när `maxFelIRad` hämtningar i följd har fallit kastas det sista felet,
 * så att ett riktigt avbrott ändå blir ett besked.
 *
 * Returnerar null för ett varv som föll och tålts.
 */
export function taligHamtning<T>(
  hamta: () => Promise<T>,
  maxFelIRad = 5
): () => Promise<T | null> {
  let felIRad = 0;
  return async () => {
    try {
      const varde = await hamta();
      felIRad = 0;
      return varde;
    } catch (orsak) {
      felIRad += 1;
      if (felIRad >= maxFelIRad) throw orsak;
      return null;
    }
  };
}
