import type { Metadata } from "next";
import { TestchattVy } from "@/components/vyer/TestchattVy";

export const metadata: Metadata = { title: "Testchatt" };

export default function Sida() {
  return <TestchattVy />;
}
