'use client';

import React from 'react';
import Markdown from '@/components/Markdown';
import { WikiPage } from '@/types/wiki';

interface WikiContentProps {
  currentPage: WikiPage | null;
  isPageLoading: boolean;
  loadingMessage?: string;
}

const WikiContent: React.FC<WikiContentProps> = ({ currentPage, isPageLoading, loadingMessage }) => {
  if (isPageLoading) {
    return (
      <div className="flex-1 p-6 overflow-y-auto" id="wiki-content">
        <div className="animate-pulse">
          <div className="h-8 bg-[var(--background)] rounded w-1/3 mb-4"></div>
          <div className="h-4 bg-[var(--background)] rounded w-full mb-2"></div>
          <div className="h-4 bg-[var(--background)] rounded w-full mb-2"></div>
          <div className="h-4 bg-[var(--background)] rounded w-5/6 mb-4"></div>
          <div className="h-32 bg-[var(--background)] rounded w-full mb-4"></div>
          <div className="h-4 bg-[var(--background)] rounded w-full mb-2"></div>
          <div className="h-4 bg-[var(--background)] rounded w-full mb-2"></div>
          <div className="h-4 bg-[var(--background)] rounded w-3/4 mb-4"></div>
        </div>
        <p className="text-sm text-[var(--muted)] mt-4">{loadingMessage || 'Loading content...'}</p>
      </div>
    );
  }

  if (!currentPage) {
    return (
      <div className="flex-1 p-6 overflow-y-auto" id="wiki-content">
        <div className="text-center py-12">
          <p className="text-[var(--muted)]">Select a page from the navigation to view its content.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 p-6 overflow-y-auto" id="wiki-content">
      <h1 className="text-2xl font-bold text-[var(--foreground)] mb-4 font-serif">{currentPage.title}</h1>
      <div className="prose prose-sm max-w-none dark:prose-invert prose-headings:font-serif prose-headings:text-[var(--foreground)] prose-p:text-[var(--foreground)] prose-a:text-[var(--accent-primary)] prose-a:no-underline hover:prose-a:underline prose-code:text-[var(--code-foreground)] prose-code:bg-[var(--code-background)] prose-code:rounded prose-code:px-1 prose-code:py-0.5 prose-pre:bg-[var(--code-block-bg)] prose-pre:text-[var(--code-block-text)] prose-pre:border prose-pre:border-[var(--border-color)] prose-strong:text-[var(--foreground)] prose-em:text-[var(--foreground)] prose-li:text-[var(--foreground)] prose-table:text-[var(--foreground)] prose-thead:text-[var(--foreground)] prose-tr:border-[var(--border-color)] prose-th:text-[var(--foreground)] prose-td:text-[var(--foreground)]">
        <Markdown content={currentPage.content} />
      </div>
      
      {currentPage.filePaths && currentPage.filePaths.length > 0 && (
        <div className="mt-8 pt-4 border-t border-[var(--border-color)]">
          <h3 className="text-sm font-semibold text-[var(--foreground)] mb-2">Related Files:</h3>
          <ul className="text-xs text-[var(--muted)] space-y-1">
            {currentPage.filePaths.map((path, index) => (
              <li key={index} className="font-mono">{path}</li>
            ))}
          </ul>
        </div>
      )}
      
      {currentPage.relatedPages && currentPage.relatedPages.length > 0 && (
        <div className="mt-4 pt-4 border-t border-[var(--border-color)]">
          <h3 className="text-sm font-semibold text-[var(--foreground)] mb-2">Related Pages:</h3>
          <ul className="text-xs text-[var(--accent-primary)] space-y-1">
            {currentPage.relatedPages.map((pageId, index) => (
              <li key={index} className="cursor-pointer hover:underline">{pageId}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default WikiContent;
