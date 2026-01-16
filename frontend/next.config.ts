/** @type {import('next').NextConfig} */
const nextConfig = {
  // Standalone output for Docker deployment
  output: 'standalone',
  // Disable the Next.js dev indicator (the "N" button in the corner)
  devIndicators: false,
};

export default nextConfig;
