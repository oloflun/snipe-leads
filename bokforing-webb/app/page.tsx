import type { Metadata } from "next";
import { OversiktVy } from "@/components/vyer/OversiktVy";

export const metadata: Metadata = { title: "Översikt" };

export default function Sida() {
  return <OversiktVy />;
}
