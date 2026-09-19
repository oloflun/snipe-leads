import type { Metadata } from "next";
import { IntegrationerVy } from "@/components/vyer/IntegrationerVy";

export const metadata: Metadata = { title: "Integrationer" };

export default function Sida() {
  return <IntegrationerVy />;
}
