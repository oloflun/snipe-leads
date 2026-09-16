import type { Metadata } from "next";
import { InkorgVy } from "@/components/vyer/InkorgVy";

export const metadata: Metadata = { title: "Inkorgen" };

export default function Page() {
  return <InkorgVy />;
}
