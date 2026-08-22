import { handlers } from "@/lib/auth";

/**
 * Auth.js egen route: /api/auth/signin, /api/auth/callback/<provider>,
 * /api/auth/session, /api/auth/csrf. OAuth-providrarnas callback-URL pekar hit.
 *
 * ANONYM MED FLIT (INV-SEC-010, ANON_ALLOWLIST). Att kräva en session för att
 * få skapa en session är en cirkel — de här endpointsen måste nå
 * oautentiserade besökare, annars går det inte att logga in.
 *
 * Det som skyddar dem är inte en sessionskontroll utan Auth.js egna grindar:
 * CSRF-token krävs på varje POST, och OAuth-callbacken verifierar `state` och
 * PKCE mot vad som skickades ut. Rate limiting på inloggningsförsök ligger
 * kvar som öppen punkt — den finns i backenden (migration 019) men inte på
 * den här ytan.
 */
export const { GET, POST } = handlers;
