import type { Metadata } from "next";
import { InkorgVy } from "@/components/vyer/InkorgVy";

export const metadata: Metadata = { title: "Inkorg" };

export default function Sida() {
  return <InkorgVy />;
}
