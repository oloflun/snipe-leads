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
  async redirects() {
    return [
      // The public demo URL that has already been shared.
      { source: "/snajp-support", destination: "/support", permanent: true },

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
