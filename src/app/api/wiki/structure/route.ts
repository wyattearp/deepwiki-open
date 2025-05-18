import { NextRequest, NextResponse } from 'next/server';
import getRepoUrl from '@/utils/getRepoUrl';

// The target backend server base URL, derived from environment variable or defaulted.
const TARGET_SERVER_BASE_URL = process.env.SERVER_BASE_URL || 'http://localhost:8001';

export async function POST(req: NextRequest) {
  try {
    const requestBody = await req.json();
    const targetUrl = `${TARGET_SERVER_BASE_URL}/api/wiki/structure`;

    // Extract repo info and other parameters
    const { repoInfo, language, provider, model, excludedDirs, excludedFiles } = requestBody;

    // Prepare the request body for the backend
    const backendRequestBody = {
      repo_url: getRepoUrl(repoInfo),
      language,
      provider,
      model,
      excluded_dirs: excludedDirs ? excludedDirs.split(',').map((dir: string) => dir.trim()) : [],
      excluded_files: excludedFiles ? excludedFiles.split(',').map((file: string) => file.trim()) : [],
    };

    // Add token if available
    if (repoInfo.token) {
      backendRequestBody.token = repoInfo.token;
    }

    // Add repo type
    if (repoInfo.type) {
      backendRequestBody.type = repoInfo.type;
    }

    // Make the actual request to the backend service
    const backendResponse = await fetch(targetUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(backendRequestBody),
    });

    // If the backend service responds with an error
    if (!backendResponse.ok) {
      const errorData = await backendResponse.json().catch(() => ({ error: backendResponse.statusText }));
      return NextResponse.json(
        { error: errorData.error || `Backend service responded with status: ${backendResponse.status}` },
        { status: backendResponse.status }
      );
    }

    // Return the successful response
    const data = await backendResponse.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error in API route (/api/wiki/structure):', error);
    let errorMessage = 'Internal Server Error';
    if (error instanceof Error) {
      errorMessage = error.message;
    }
    return NextResponse.json({ error: errorMessage }, { status: 500 });
  }
}
