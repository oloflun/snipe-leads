import type { Metadata } from "next";
import { IntakterUtgifterVy } from "@/components/vyer/IntakterUtgifterVy";

export const metadata: Metadata = { title: "Intäkter & utgifter" };

export default function Sida() {
  return <IntakterUtgifterVy />;
}
