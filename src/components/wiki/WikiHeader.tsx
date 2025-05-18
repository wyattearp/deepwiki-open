'use client';

import React from 'react';
import Link from 'next/link';
import { FaHome, FaGithub, FaGitlab, FaBitbucket, FaFolder } from 'react-icons/fa';
import ThemeToggle from '@/components/theme-toggle';
import { RepoInfo } from '@/types/repoinfo';
import { useLanguage } from '@/contexts/LanguageContext';

interface WikiHeaderProps {
  repoInfo: RepoInfo;
  onOpenModelSelection: () => void;
}

const WikiHeader: React.FC<WikiHeaderProps> = ({ repoInfo, onOpenModelSelection }) => {
  const { messages } = useLanguage();

  return (
    <header className="max-w-[90%] xl:max-w-[1400px] mx-auto mb-8 h-fit w-full">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="flex items-center gap-4">
          <Link href="/" className="text-[var(--accent-primary)] hover:text-[var(--highlight)] flex items-center gap-1.5 transition-colors border-b border-[var(--border-color)] hover:border-[var(--accent-primary)] pb-0.5">
            <FaHome /> {messages.repoPage?.home || 'Home'}
          </Link>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={onOpenModelSelection}
            className="text-xs px-3 py-1.5 bg-[var(--background)] text-[var(--foreground)] rounded-md hover:bg-[var(--background)]/80 border border-[var(--border-color)] transition-colors"
          >
            {messages.repoPage?.settings || 'Settings'}
          </button>
          <ThemeToggle />
        </div>
      </div>

      {/* Display repository info */}
      <div className="text-xs text-[var(--muted)] mb-5 flex items-center mt-4">
        {repoInfo.type === 'local' ? (
          <div className="flex items-center">
            <FaFolder className="mr-2" />
            <span className="break-all">{repoInfo.localPath}</span>
          </div>
        ) : (
          <>
            {repoInfo.type === 'github' ? (
              <FaGithub className="mr-2" />
            ) : repoInfo.type === 'gitlab' ? (
              <FaGitlab className="mr-2" />
            ) : (
              <FaBitbucket className="mr-2" />
            )}
            <a
              href={repoInfo.repoUrl ?? ''}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-[var(--accent-primary)] transition-colors border-b border-[var(--border-color)] hover:border-[var(--accent-primary)]"
            >
              {repoInfo.owner}/{repoInfo.repo}
            </a>
          </>
        )}
      </div>
    </header>
  );
};

export default WikiHeader;
