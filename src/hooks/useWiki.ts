'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { RepoInfo } from '@/types/repoinfo';
import { WikiStructure, WikiPage } from '@/types/wiki';
import { WikiService } from '@/services/WikiService';

interface UseWikiProps {
  repoInfo: RepoInfo;
  language: string;
  provider: string;
  model: string;
  isCustomModel: boolean;
  customModel: string;
  excludedDirs: string;
  excludedFiles: string;
  isComprehensiveView: boolean;
}

interface UseWikiReturn {
  isLoading: boolean;
  error: Error | null;
  loadingMessage: string;
  wikiStructure: WikiStructure | null;
  generatedPages: Record<string, WikiPage>;
  currentPageId: string;
  setCurrentPageId: (pageId: string) => void;
  pagesInProgress: Set<string>;
  refreshWiki: () => Promise<void>;
  exportWikiAsJson: () => Promise<void>;
  exportWikiAsMarkdown: () => Promise<void>;
  exportError: string | null;
  isRefreshing: boolean;
}

export function useWiki({
  repoInfo,
  language,
  provider,
  model,
  isCustomModel,
  customModel,
  excludedDirs,
  excludedFiles,
  isComprehensiveView,
}: UseWikiProps): UseWikiReturn {
  // State variables
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [loadingMessage, setLoadingMessage] = useState<string>('Initializing wiki generation...');
  const [wikiStructure, setWikiStructure] = useState<WikiStructure | null>(null);
  const [generatedPages, setGeneratedPages] = useState<Record<string, WikiPage>>({});
  const [currentPageId, setCurrentPageId] = useState<string>('');
  const [pagesInProgress, setPagesInProgress] = useState<Set<string>>(new Set());
  const [exportError, setExportError] = useState<string | null>(null);

  // Refs
  const activeContentRequests = useRef<Map<string, boolean>>(new Map());
  const cacheLoadedSuccessfully = useRef(false);
  const effectRan = useRef(false);

  // Load wiki from cache or generate it
  useEffect(() => {
    if (effectRan.current === false) {
      effectRan.current = true;
      loadWiki();
    }
  }, [repoInfo.owner, repoInfo.repo, repoInfo.type, language]);

  // Function to load wiki from cache or generate it
  const loadWiki = async () => {
    setIsLoading(true);
    setError(null);
    setLoadingMessage('Initializing wiki generation...');

    try {
      // Try to load from cache first
      const cachedData = await WikiService.getWikiCache(
        repoInfo.owner,
        repoInfo.repo,
        repoInfo.type,
        language
      );

      if (cachedData) {
        setWikiStructure(cachedData.wikiStructure);
        setGeneratedPages(cachedData.generatedPages);
        
        // Set the first page as the current page if not already set
        if (!currentPageId && cachedData.wikiStructure.pages.length > 0) {
          setCurrentPageId(cachedData.wikiStructure.pages[0].id);
        }
        
        cacheLoadedSuccessfully.current = true;
        setIsLoading(false);
        return;
      }

      // If not in cache, generate the wiki structure
      setLoadingMessage('Analyzing repository structure...');
      const structure = await WikiService.generateWikiStructure(
        repoInfo,
        language,
        provider,
        model,
        isCustomModel,
        customModel,
        excludedDirs,
        excludedFiles
      );

      setWikiStructure(structure);
      
      // Set the first page as the current page
      if (structure.pages.length > 0) {
        setCurrentPageId(structure.pages[0].id);
      }

      // Generate content for each page
      await generateAllPages(structure);

      // Save to cache
      await saveToCache();

      setIsLoading(false);
    } catch (err) {
      console.error('Error loading wiki:', err);
      setError(err instanceof Error ? err : new Error('Failed to load wiki'));
      setIsLoading(false);
    }
  };

  // Function to generate content for all pages
  const generateAllPages = async (structure: WikiStructure) => {
    const pages: Record<string, WikiPage> = {};
    
    // Initialize pages with empty content
    structure.pages.forEach(page => {
      pages[page.id] = { ...page, content: 'Loading...' };
    });
    
    setGeneratedPages(pages);
    
    // Generate content for each page
    for (const page of structure.pages) {
      if (isComprehensiveView || page.importance === 'high') {
        await generatePageContent(page);
      }
    }
  };

  // Function to generate content for a single page
  const generatePageContent = async (page: WikiPage) => {
    // Skip if already being processed
    if (activeContentRequests.current.get(page.id)) {
      return;
    }
    
    // Mark this page as being processed
    activeContentRequests.current.set(page.id, true);
    setPagesInProgress(prev => new Set(prev).add(page.id));
    
    try {
      setLoadingMessage(`Generating content for "${page.title}"...`);
      
      const content = await WikiService.generatePageContent(
        repoInfo,
        page,
        language,
        provider,
        model,
        isCustomModel,
        customModel
      );
      
      // Update the page with the generated content
      setGeneratedPages(prev => ({
        ...prev,
        [page.id]: { ...page, content }
      }));
    } catch (err) {
      console.error(`Error generating content for page ${page.id}:`, err);
      
      // Update the page with an error message
      setGeneratedPages(prev => ({
        ...prev,
        [page.id]: { 
          ...page, 
          content: `Error generating content: ${err instanceof Error ? err.message : 'Unknown error'}`
        }
      }));
    } finally {
      // Mark this page as no longer being processed
      activeContentRequests.current.delete(page.id);
      setPagesInProgress(prev => {
        const newSet = new Set(prev);
        newSet.delete(page.id);
        return newSet;
      });
    }
  };

  // Function to save wiki to cache
  const saveToCache = async () => {
    if (!isLoading && !error && wikiStructure && Object.keys(generatedPages).length > 0) {
      // Only save if we didn't just load from cache
      if (!cacheLoadedSuccessfully.current) {
        try {
          await WikiService.saveWikiCache(
            repoInfo.owner,
            repoInfo.repo,
            repoInfo.type,
            language,
            wikiStructure,
            generatedPages
          );
          console.log('Wiki saved to cache successfully');
        } catch (error) {
          console.error('Error saving to server cache:', error);
        }
      }
    }
  };

  // Function to refresh the wiki
  const refreshWiki = async () => {
    setIsRefreshing(true);
    cacheLoadedSuccessfully.current = false;
    
    try {
      await loadWiki();
    } finally {
      setIsRefreshing(false);
    }
  };

  // Function to export wiki as JSON
  const exportWikiAsJson = async () => {
    setExportError(null);
    
    try {
      if (!wikiStructure) {
        throw new Error('Wiki structure not available');
      }
      
      const pages = Object.values(generatedPages);
      const blob = await WikiService.exportWiki(
        repoInfo.repoUrl || `${repoInfo.owner}/${repoInfo.repo}`,
        pages,
        'json'
      );
      
      // Create a download link
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${repoInfo.repo}_wiki.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Error exporting wiki as JSON:', err);
      setExportError(err instanceof Error ? err.message : 'Failed to export wiki');
    }
  };

  // Function to export wiki as Markdown
  const exportWikiAsMarkdown = async () => {
    setExportError(null);
    
    try {
      if (!wikiStructure) {
        throw new Error('Wiki structure not available');
      }
      
      const pages = Object.values(generatedPages);
      const blob = await WikiService.exportWiki(
        repoInfo.repoUrl || `${repoInfo.owner}/${repoInfo.repo}`,
        pages,
        'markdown'
      );
      
      // Create a download link
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${repoInfo.repo}_wiki.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Error exporting wiki as Markdown:', err);
      setExportError(err instanceof Error ? err.message : 'Failed to export wiki');
    }
  };

  // Save to cache when wiki changes
  useEffect(() => {
    saveToCache();
  }, [isLoading, error, wikiStructure, generatedPages]);

  // Scroll to top when currentPageId changes
  useEffect(() => {
    const wikiContent = document.getElementById('wiki-content');
    if (wikiContent) {
      wikiContent.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }, [currentPageId]);

  return {
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
    isRefreshing,
  };
}
