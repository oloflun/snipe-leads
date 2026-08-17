import { OnboardingView } from "@/components/WorkspaceViews";
import { redirectIfOnboarded } from "@/lib/auth/onboarding-gate";

export default async function Page() {
  // Den som redan är klar ska inte fastna här. Kontrollen låg i proxyn och
  // läste ett sessionsanspråk; nu läses den färskt.
  await redirectIfOnboarded();
  return <OnboardingView />;
}
