import type { Metadata } from "next";
import { GranskningVy } from "@/components/vyer/GranskningVy";

export const metadata: Metadata = { title: "Granskning" };

export default function Sida() {
  return <GranskningVy />;
}
