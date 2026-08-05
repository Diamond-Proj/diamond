import { NextResponse } from 'next/server';

// GET method to retrieve health status and git information
export async function GET() {
  try {
    const currentDateTime = new Date().toISOString();
    
    // Get git commit SHA for deployment
    const gitCommitSha = process.env.VERCEL_GIT_COMMIT_SHA;
    let healthData;

    if (gitCommitSha && typeof gitCommitSha === 'string' && gitCommitSha.length === 40) {
      healthData = {
        status: 'healthy',
        timestamp: currentDateTime,
        git: {
          commit_sha: gitCommitSha
        }
      };
      return NextResponse.json(healthData, { status: 200 });

    } else {
      healthData = {
        status: 'unhealthy',
        timestamp: currentDateTime,
        git: {
          commit_sha: 'unknown'
        }
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
