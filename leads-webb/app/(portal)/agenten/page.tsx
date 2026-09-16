import type { Metadata } from "next";
import { AgentVy } from "@/components/vyer/AgentVy";

export const metadata: Metadata = { title: "Kör agenten" };

export default function Sida() {
  return <AgentVy />;
}
