import { Suspense } from "react";
import { LoginView } from "@/components/WorkspaceViews";

export default function Page() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-paper" />}>
      <LoginView />
    </Suspense>
  );
}
