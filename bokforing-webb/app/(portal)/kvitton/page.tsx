import type { Metadata } from "next";
import { KvittolistaVy } from "@/components/vyer/KvittolistaVy";

export const metadata: Metadata = { title: "Kvitton" };

export default function Page() {
  return <KvittolistaVy />;
}
