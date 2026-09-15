import type { Metadata } from "next";
import { ListorVy } from "@/components/vyer/ListorVy";

export const metadata: Metadata = { title: "Leadslistor" };

export default function Sida() {
  return <ListorVy />;
}
