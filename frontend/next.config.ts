import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'standalone',
  rewrites: async () => {
    return {
      beforeFiles: [
        {
          source: '/api/:path*',
          destination: 'http://localhost:5000/api/:path*',
        },
      ],
    };
  },
};

export default nextConfig;
