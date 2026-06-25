import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  typescript: {
    // Disable typechecking during build to save memory on small EC2 servers
    ignoreBuildErrors: true,
  },
};

export default nextConfig;
