import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  reactCompiler: true,
  experimental: {
    // The /api rewrite proxy defaults to a 30s timeout. Task submission with a
    // file upload performs two sequential Globus Compute round trips (staging
    // + sbatch), which routinely exceeds 30s and made the proxy return a 504
    // while the backend went on to submit the task successfully.
    //
    // Capped at 120s to match Vercel's proxied-request timeout ceiling
    // (https://vercel.com/docs/limits#proxied-request-timeout); a larger value
    // would be silently truncated to 120s in production, so keep them aligned.
    proxyTimeout: 120_000
  },
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'avatars.githubusercontent.com'
      },
      {
        protocol: 'https',
        hostname: 'avatar.vercel.sh'
      }
    ]
  },
  rewrites: async () => {
    const flaskUrl = process.env.FLASK_URL || 'localhost:5328';
    // Use HTTPS for production domains, HTTP for localhost
    const protocol = flaskUrl.includes('localhost') ? 'http' : 'https';
    const baseUrl = flaskUrl.startsWith('http')
      ? flaskUrl
      : `${protocol}://${flaskUrl}`;
    // console.log('baseUrl: ', baseUrl);
    return [
      {
        source: '/api/:path*',
        destination: `${baseUrl}/api/:path*`
      }
    ];
  }
};

export default nextConfig;
