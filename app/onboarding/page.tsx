import { OnboardingWizard } from "@/components/auth/OnboardingWizard";
import { auth } from "@/lib/auth";
import { redirectIfOnboarded } from "@/lib/auth/onboarding-gate";

export default async function Page() {
  // Den som redan är klar ska inte fastna här. Kontrollen låg i proxyn och
  // läste ett sessionsanspråk; nu läses den färskt.
  await redirectIfOnboarded();

  // Kontots namn och adress förifyller kontaktpersonssteget: den som
  // registrerar sig ÄR oftast kontaktpersonen, och ett förifyllt SANT värde
  // är motsatsen till det gamla formulärets påhittade defaultar.
  const session = await auth();

  return (
    <main className="min-h-screen bg-paper text-ink">
      <div className="mx-auto max-w-[1480px] px-6 py-10 md:px-8">
        <OnboardingWizard
          epost={session?.user?.email ?? null}
          namn={session?.user?.name ?? null}
        />
      </div>
    </main>
  );
}
