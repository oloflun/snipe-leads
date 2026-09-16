import type { Metadata } from "next";
import { DemoVy } from "@/components/vyer/DemoVy";

export const metadata: Metadata = { title: "Se Iris arbeta" };

export default function Page() {
  return <DemoVy />;
}
