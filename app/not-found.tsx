import { ButtonLink, EmptyState } from "@/components/ui";

export default function NotFound() {
  return (
    <main className="grid min-h-screen place-items-center bg-paper p-6">
      <div className="max-w-lg">
        <EmptyState title="Sidan finns inte" body="Route-strukturen är skapad, men den här adressen matchar ingen vy i Snipra." />
        <div className="mt-5 flex justify-center">
          <ButtonLink href="/dashboard">Till dashboard</ButtonLink>
        </div>
      </div>
    </main>
  );
}
