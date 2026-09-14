import type { Metadata } from "next";
import { DokumentVy } from "@/components/vyer/DokumentVy";

export const metadata: Metadata = { title: "PDF-filer" };

export default function Sida() {
  return <DokumentVy />;
}
