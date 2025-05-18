'use client';

import React, { useState, useMemo, useRef } from 'react';
import { useParams, useSearchParams } from 'next/navigation';
import { FaComments, FaTimes } from 'react-icons/fa';
import Ask from '@/components/Ask';
import ModelSelectionModal from '@/components/ModelSelectionModal';
import { useLanguage } from '@/contexts/LanguageContext';
import { RepoInfo } from '@/types/repoinfo';

// Import wiki components
import WikiHeader from '@/components/wiki/WikiHeader';
import WikiNavigation from '@/components/wiki/WikiNavigation';
import WikiContent from '@/components/wiki/WikiContent';
import WikiLoading from '@/components/wiki/WikiLoading';
import WikiError from '@/components/wiki/WikiError';

// Import hooks
import { useWiki } from '@/hooks/useWiki';

// Add CSS styles for wiki with Japanese aesthetic
const wikiStyles = `
  .prose code {
    @apply bg-[var(--code-background)] text-[var(--code-foreground)] px-1.5 py-0.5 rounded text-sm font-mono;
  }

  .prose pre {
    @apply bg-[var(--code-block-bg)] text-[var(--code-block-text)] p-4 rounded-md overflow-x-auto border border-[var(--border-color)];
  }

  .prose pre code {
    @apply bg-transparent text-inherit p-0 text-sm leading-relaxed;
  }

  .prose h1, .prose h2, .prose h3, .prose h4, .prose h5, .prose h6 {
    @apply font-serif text-[var(--foreground)] font-bold;
  }

  .prose h1 {
    @apply text-2xl mb-6 pb-2 border-b border-[var(--border-color)];
  }

  .prose h2 {
    @apply text-xl mt-8 mb-4 pb-1 border-b border-[var(--border-color)];
  }

  .prose h3 {
    @apply text-lg mt-6 mb-3;
  }

  .prose p {
    @apply text-[var(--foreground)] mb-4 leading-relaxed;
  }

  .prose a {
    @apply text-[var(--accent-primary)] no-underline border-b border-[var(--border-color)] hover:border-[var(--accent-primary)] transition-colors;
  }

  .prose blockquote {
    @apply border-l-4 border-[var(--accent-primary)]/30 bg-[var(--background)]/30 pl-4 py-1 italic;
  }

  .prose ul, .prose ol {
    @apply text-[var(--foreground)];
  }

  .prose table {
    @apply border-collapse border border-[var(--border-color)];
  }

  .prose th {
    @apply bg-[var(--background)]/70 text-[var(--foreground)] p-2 border border-[var(--border-color)];
  }

  .prose td {
    @apply p-2 border border-[var(--border-color)];
  }
`;

export default function RepoWikiPage() {
  // Get route parameters and search params
  const params = useParams();
  const searchParams = useSearchParams();

  // Extract owner and repo from route params
  const owner = params.owner as string;
  const repo = params.repo as string;

  // Extract tokens from search params
  const token = searchParams.get('token') || '';
  const repoType = searchParams.get('type') || 'github';
  const localPath = searchParams.get('local_path') ? decodeURIComponent(searchParams.get('local_path') || '') : undefined;
  const repoUrl = searchParams.get('repo_url') ? decodeURIComponent(searchParams.get('repo_url') || '') : undefined;
  const providerParam = searchParams.get('provider') || '';
  const modelParam = searchParams.get('model') || '';
  const isCustomModelParam = searchParams.get('is_custom_model') === 'true';
  const customModelParam = searchParams.get('custom_model') || '';
  const language = searchParams.get('language') || 'en';

  // Import language context for translations
  const { messages } = useLanguage();

  // Initialize repo info
  const repoInfo = useMemo<RepoInfo>(() => ({
    owner,
    repo,
    type: repoType,
    token: token || null,
    localPath: localPath || null,
    repoUrl: repoUrl || null
  }), [owner, repo, repoType, localPath, repoUrl, token]);

  // Model selection state variables
  const [selectedProviderState, setSelectedProviderState] = useState(providerParam || 'google');
  const [selectedModelState, setSelectedModelState] = useState(modelParam || 'gemini-1.5-pro');
  const [isCustomSelectedModelState, setIsCustomSelectedModelState] = useState(isCustomModelParam);
  const [customSelectedModelState, setCustomSelectedModelState] = useState(customModelParam);
  const [isModelSelectionModalOpen, setIsModelSelectionModalOpen] = useState(false);

  // Wiki type state - default to comprehensive view
  const isComprehensiveParam = searchParams.get('comprehensive') !== 'false';
  const [isComprehensiveView, setIsComprehensiveView] = useState(isComprehensiveParam);

  // File filter state
  const excludedDirs = searchParams.get('excluded_dirs') || '';
  const excludedFiles = searchParams.get('excluded_files') || '';
  const [modelExcludedDirs, setModelExcludedDirs] = useState(excludedDirs);
  const [modelExcludedFiles, setModelExcludedFiles] = useState(excludedFiles);

  // State for Ask modal
  const [isAskModalOpen, setIsAskModalOpen] = useState(false);
  const askComponentRef = useRef<{ clearConversation: () => void } | null>(null);

  // Use the wiki hook to manage wiki state
  const {
    isLoading,
    error,
    loadingMessage,
    wikiStructure,
    generatedPages,
    currentPageId,
    setCurrentPageId,
    pagesInProgress,
    refreshWiki,
    exportWikiAsJson,
    exportWikiAsMarkdown,
    exportError,
    isRefreshing
  } = useWiki({
    repoInfo,
    language,
    provider: selectedProviderState,
    model: selectedModelState,
    isCustomModel: isCustomSelectedModelState,
    customModel: customSelectedModelState,
    excludedDirs: modelExcludedDirs,
    excludedFiles: modelExcludedFiles,
    isComprehensiveView
  });

  // Handle model selection modal apply
  const handleModelSelectionApply = () => {
    setIsModelSelectionModalOpen(false);
    refreshWiki();
  };

  // Get the current page
  const currentPage = currentPageId ? generatedPages[currentPageId] : null;
  const isPageLoading = currentPageId ? pagesInProgress.has(currentPageId) : false;

  return (
    <div className="h-screen paper-texture p-4 md:p-8 flex flex-col">
      <style>{wikiStyles}</style>

      {/* Header */}
      <WikiHeader
        repoInfo={repoInfo}
        onOpenModelSelection={() => setIsModelSelectionModalOpen(true)}
      />

      {/* Main content */}
      {isLoading ? (
        <WikiLoading loadingMessage={loadingMessage} />
      ) : error ? (
        <WikiError error={error} messages={messages} />
      ) : wikiStructure ? (
        <div className="h-full overflow-y-auto flex flex-col lg:flex-row gap-4 w-full overflow-hidden bg-[var(--card-bg)] rounded-lg shadow-custom card-japanese">
          {/* Wiki Navigation */}
          <WikiNavigation
            wikiStructure={wikiStructure}
            currentPageId={currentPageId}
            onPageSelect={setCurrentPageId}
            onExportJson={exportWikiAsJson}
            onExportMarkdown={exportWikiAsMarkdown}
            onRefresh={refreshWiki}
            isRefreshing={isRefreshing}
            exportError={exportError}
            messages={messages.repoPage}
          />

          {/* Wiki Content */}
          <WikiContent
            currentPage={currentPage}
            isPageLoading={isPageLoading}
            loadingMessage={`Generating content for "${currentPage?.title}"...`}
          />

          {/* Ask button */}
          <button
            onClick={() => setIsAskModalOpen(true)}
            className="fixed bottom-6 right-6 bg-[var(--accent-primary)] text-white p-3 rounded-full shadow-lg hover:bg-[var(--accent-primary)]/90 transition-colors z-10"
            aria-label="Ask about this repository"
          >
            <FaComments className="text-xl" />
          </button>
        </div>
      ) : null}

      {/* Ask Modal */}
      <div className={`fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 transition-opacity duration-300 ${isAskModalOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'}`}>
        <div className="bg-[var(--card-bg)] rounded-lg shadow-xl w-full max-w-3xl max-h-[80vh] flex flex-col">
          <div className="flex items-center justify-end p-3 absolute top-0 right-0 z-10">
            <button
              onClick={() => setIsAskModalOpen(false)}
              className="text-[var(--muted)] hover:text-[var(--foreground)] transition-colors bg-[var(--card-bg)]/80 rounded-full p-2"
              aria-label="Close"
            >
              <FaTimes className="text-xl" />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            <Ask
              repoInfo={repoInfo}
              provider={selectedProviderState}
              model={selectedModelState}
              isCustomModel={isCustomSelectedModelState}
              customModel={customSelectedModelState}
              language={language}
              onRef={(ref) => (askComponentRef.current = ref)}
            />
          </div>
        </div>
      </div>

      {/* Model Selection Modal */}
      <ModelSelectionModal
        isOpen={isModelSelectionModalOpen}
        onClose={() => setIsModelSelectionModalOpen(false)}
        provider={selectedProviderState}
        setProvider={setSelectedProviderState}
        model={selectedModelState}
        setModel={setSelectedModelState}
        isCustomModel={isCustomSelectedModelState}
        setIsCustomModel={setIsCustomSelectedModelState}
        customModel={customSelectedModelState}
        setCustomModel={setCustomSelectedModelState}
        isComprehensiveView={isComprehensiveView}
        setIsComprehensiveView={setIsComprehensiveView}
        showFileFilters={true}
        excludedDirs={modelExcludedDirs}
        setExcludedDirs={setModelExcludedDirs}
        excludedFiles={modelExcludedFiles}
        setExcludedFiles={setModelExcludedFiles}
        onApply={handleModelSelectionApply}
      />
    </div>
  );
}
