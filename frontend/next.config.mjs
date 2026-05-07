/** @type {import('next').NextConfig} */
const raw = process.env.NEXT_PUBLIC_BASE_PATH ?? "";
const basePath = raw.trim().replace(/\/+$/, "");

const nextConfig = {
  output: "standalone",
  basePath: basePath || undefined,
};

export default nextConfig;
