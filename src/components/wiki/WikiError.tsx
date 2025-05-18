'use client';

import React from 'react';
import Link from 'next/link';
import { FaExclamationTriangle, FaHome } from 'react-icons/fa';

interface WikiErrorProps {
  error: Error | null;
  messages: any;
}

const WikiError: React.FC<WikiErrorProps> = ({ error, messages }) => {
  return (
    <div className="flex flex-col items-center justify-center h-full p-8">
      <div className="text-[var(--highlight)] mb-4">
        <FaExclamationTriangle className="text-4xl" />
      </div>
      <h2 className="text-xl font-bold text-[var(--foreground)] mb-2">
        {messages.repoPage?.errorTitle || 'Error Loading Repository'}
      </h2>
      <p className="text-[var(--muted)] text-center mb-6 max-w-md">
        {error?.message || messages.repoPage?.errorMessageDefault || 'Please check that your repository exists and is public. Valid formats are "owner/repo", "https://github.com/owner/repo", "https://gitlab.com/owner/repo", "https://bitbucket.org/owner/repo", or local folder paths like "C:\\path\\to\\folder" or "/path/to/folder".'}
      </p>
      <div className="mt-5">
        <Link
          href="/"
          className="btn-japanese px-5 py-2 inline-flex items-center gap-1.5"
        >
          <FaHome className="text-sm" />
          {messages.repoPage?.backToHome || 'Back to Home'}
        </Link>
      </div>
    </div>
  );
};

export default WikiError;
