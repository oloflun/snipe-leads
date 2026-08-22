import type { NextConfig } from "next";

/**
 * Route map moved in the Snajp redesign:
 *   /leads, /support        → public product pages (were: authenticated workspace)
 *   /dashboard/<slug>       → the authenticated workspace (was: top-level slugs)
 *   /snajp-support          → /support (that path is public and already shared)
 *
 * Every old path keeps working. 308 preserves the method and tells crawlers the
 * move is permanent.
 */
const workspaceSlugs = [
  "companies",
  "contacts",
  "campaigns",
  "emails",
  "analytics",
  "inbox",
  "assistant"
];

const nextConfig: NextConfig = {
  async headers() {
    return [
      {
        /**
         * Service workern får ALDRIG cachas länge.
         *
         * Webbläsaren hämtar `/sw.js` för att upptäcka en ny version. Ligger
         * den i HTTP-cachen kan en gammal worker sitta kvar i upp till 24
         * timmar efter en deploy — och en gammal worker serverar en gammal
         * offline-sida och ett gammalt cachenamn. `no-cache` betyder inte
         * "cacha inte", utan "fråga servern varje gång", vilket är exakt det
         * som behövs.
         */
        source: "/sw.js",
        headers: [
          { key: "Cache-Control", value: "no-cache, must-revalidate" },
          { key: "Service-Worker-Allowed", value: "/" }
        ]
      }
    ];
  },

  async redirects() {
    return [
      // The public demo URL that has already been shared.
      { source: "/snajp-support", destination: "/support", permanent: true },

      // Inställningar som flyttat in i inställningarna.
      //
      // "Målgrupp och autonomi" låg på en /dashboard-väg trots att den är en
      // inställning. Det gjorde att inställningsmenyns länk lämnade
      // inställningarna — och för en plattformsadmin skickar
      // app/dashboard/layout.tsx den vägen rakt till /admin, alltså till
      // Översikt. Den var därför omöjlig att öppna från menyn.
      { source: "/dashboard/leads/kontroll", destination: "/settings/leads", permanent: true },
      // Gamla namn på sidor som bytt adress i omstruktureringen. En inställning
      // som flyttas men försvinner är värre än en som ligger fel.
      { source: "/settings/general", destination: "/settings/affarskontext", permanent: true },

      // Legacy top-level workspace routes now live under /dashboard.
      ...workspaceSlugs.map((slug) => ({
        source: `/${slug}`,
        destination: `/dashboard/${slug}`,
        permanent: true
      })),
      ...workspaceSlugs.map((slug) => ({
        source: `/${slug}/:path*`,
        destination: `/dashboard/${slug}/:path*`,
        permanent: true
      }))

      // NOTE: /leads is deliberately absent. It is now a public product page, not a
      // redirect — signed-in users reach the workspace through the dashboard nav.
    ];
  }
};

export default nextConfig;
