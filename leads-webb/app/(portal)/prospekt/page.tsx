import type { Metadata } from "next";
import { ProspektVy } from "@/components/vyer/ProspektVy";

export const metadata: Metadata = { title: "Prospekt" };

export default function Sida() {
  return <ProspektVy />;
}
