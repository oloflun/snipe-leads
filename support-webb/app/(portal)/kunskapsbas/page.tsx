import type { Metadata } from "next";
import { KunskapsbasVy } from "@/components/vyer/KunskapsbasVy";

export const metadata: Metadata = { title: "Kunskapsbas" };

export default function Sida() {
  return <KunskapsbasVy />;
}
