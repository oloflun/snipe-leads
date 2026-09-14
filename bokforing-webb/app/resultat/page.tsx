import type { Metadata } from "next";
import { ResultatVy } from "@/components/vyer/ResultatVy";

export const metadata: Metadata = { title: "Resultat" };

export default function Sida() {
  return <ResultatVy />;
}
