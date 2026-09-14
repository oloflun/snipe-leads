import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Appen bor i ett underbibliotek av snipe-leads-repot, och utan en
  // uttalad rot härleder Next projektroten ur repots lockfil — och hittar
  // då huvudappens proxy.ts (Auth.js-beroende) och kraschar. Roten är HÄR.
  turbopack: {
    root: path.join(__dirname)
  },
  outputFileTracingRoot: path.join(__dirname)
};

export default nextConfig;
