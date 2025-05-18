'use client';

import React from 'react';
import { FaBookOpen } from 'react-icons/fa';

interface WikiLoadingProps {
  loadingMessage: string;
}

const WikiLoading: React.FC<WikiLoadingProps> = ({ loadingMessage }) => {
  return (
    <div className="flex flex-col items-center justify-center h-full p-8">
      <div className="text-[var(--accent-primary)] mb-4">
        <FaBookOpen className="text-4xl animate-pulse" />
      </div>
      <h2 className="text-xl font-bold text-[var(--foreground)] mb-2">Generating Wiki</h2>
      <p className="text-[var(--muted)] text-center mb-4">{loadingMessage}</p>
      <div className="w-64 h-2 bg-[var(--background)] rounded-full overflow-hidden">
        <div className="h-full bg-[var(--accent-primary)] animate-pulse-width"></div>
      </div>
      <style jsx>{`
        @keyframes pulse-width {
          0% { width: 15%; }
          50% { width: 85%; }
          100% { width: 15%; }
        }
        .animate-pulse-width {
          animation: pulse-width 2s ease-in-out infinite;
        }
      `}</style>
    </div>
  );
};

export default WikiLoading;
