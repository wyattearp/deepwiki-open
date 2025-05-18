'use client';

import React from 'react';
import { FaFileExport, FaSync } from 'react-icons/fa';
import WikiTreeView from '@/components/WikiTreeView';
import { WikiStructure } from '@/types/wiki';

interface WikiNavigationProps {
  wikiStructure: WikiStructure;
  currentPageId: string;
  onPageSelect: (pageId: string) => void;
  onExportJson: () => void;
  onExportMarkdown: () => void;
  onRefresh: () => void;
  isRefreshing: boolean;
  exportError: string | null;
  messages: any;
}

const WikiNavigation: React.FC<WikiNavigationProps> = ({
  wikiStructure,
  currentPageId,
  onPageSelect,
  onExportJson,
  onExportMarkdown,
  onRefresh,
  isRefreshing,
  exportError,
  messages
}) => {
  return (
    <div className="w-full lg:w-64 xl:w-72 h-full overflow-y-auto p-4 border-r border-[var(--border-color)] bg-[var(--background)]/30">
      <div className="mb-4">
        <h3 className="text-lg font-bold text-[var(--foreground)] mb-2 font-serif">
          {wikiStructure.title}
        </h3>
        <p className="text-xs text-[var(--muted)] mb-4">
          {wikiStructure.description}
        </p>

        {/* Export and refresh buttons */}
        <div className="flex flex-col gap-2 mb-4">
          <div className="flex items-center gap-2">
            <button
              onClick={onRefresh}
              disabled={isRefreshing}
              className="flex items-center text-xs px-3 py-2 bg-[var(--background)] text-[var(--foreground)] rounded-md hover:bg-[var(--background)]/80 disabled:opacity-50 disabled:cursor-not-allowed border border-[var(--border-color)] transition-colors"
            >
              <FaSync className={`mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
              {messages?.refresh || 'Refresh'}
            </button>
          </div>

          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <button
                onClick={onExportMarkdown}
                className="flex items-center text-xs px-3 py-2 bg-[var(--background)] text-[var(--foreground)] rounded-md hover:bg-[var(--background)]/80 disabled:opacity-50 disabled:cursor-not-allowed border border-[var(--border-color)] transition-colors"
              >
                <FaFileExport className="mr-2" />
                {messages?.exportAsMarkdown || 'Export as Markdown'}
              </button>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={onExportJson}
                className="flex items-center text-xs px-3 py-2 bg-[var(--background)] text-[var(--foreground)] rounded-md hover:bg-[var(--background)]/80 disabled:opacity-50 disabled:cursor-not-allowed border border-[var(--border-color)] transition-colors"
              >
                <FaFileExport className="mr-2" />
                {messages?.exportAsJson || 'Export as JSON'}
              </button>
            </div>
          </div>
          {exportError && (
            <div className="mt-2 text-xs text-[var(--highlight)]">
              {exportError}
            </div>
          )}
        </div>
      </div>

      <h4 className="text-md font-semibold text-[var(--foreground)] mb-3 font-serif">
        {messages?.pages || 'Pages'}
      </h4>
      <WikiTreeView
        wikiStructure={wikiStructure}
        currentPageId={currentPageId}
        onPageSelect={onPageSelect}
        messages={messages}
      />
    </div>
  );
};

export default WikiNavigation;
