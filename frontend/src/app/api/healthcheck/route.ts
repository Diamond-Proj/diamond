import { NextResponse } from 'next/server';

// Fetch the Flask backend's healthcheck directly. Going through /api would hit
// this route instead of the rewrite, so resolve FLASK_URL like next.config.ts.
async function fetchBackendHealth() {
  const flaskUrl = process.env.FLASK_URL || 'localhost:5328';
  const protocol = flaskUrl.includes('localhost') ? 'http' : 'https';
  const baseUrl = flaskUrl.startsWith('http')
    ? flaskUrl
    : `${protocol}://${flaskUrl}`;
  try {
    const res = await fetch(`${baseUrl}/api/healthcheck`, {
      cache: 'no-store',
      signal: AbortSignal.timeout(5000)
    });
    return { ...(await res.json()), http_status: res.status };
  } catch (error) {
    return { status: 'unreachable', error: (error as Error).message };
  }
}

// GET method to retrieve health status and git information
export async function GET() {
  try {
    const currentDateTime = new Date().toISOString();
    
    // Get git commit SHA for deployment
    const gitCommitSha = process.env.GIT_COMMIT_SHA;
    const backend = await fetchBackendHealth();
    let healthData;

    if (gitCommitSha && typeof gitCommitSha === 'string' && gitCommitSha.length === 40) {
      healthData = {
        status: 'healthy',
        timestamp: currentDateTime,
        git: {
          commit_sha: gitCommitSha
        },
        backend
      };
      return NextResponse.json(healthData, { status: 200 });

    } else {
      healthData = {
        status: 'unhealthy',
        timestamp: currentDateTime,
        git: {
          commit_sha: 'unknown'
        },
        backend
      };
      return NextResponse.json(healthData, { status: 500 });
    }
    
  } catch (error) {
    console.error('Error retrieving health status:', error);
    return NextResponse.json(
      { 
        status: 'unhealthy',
        timestamp: new Date().toISOString(),
        error: 'Failed to retrieve health status',
        details: (error as Error).message 
      },
      { status: 500 }
    );
  }
} 
