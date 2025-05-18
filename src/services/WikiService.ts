import { RepoInfo } from '@/types/repoinfo';
import { WikiStructure, WikiPage } from '@/types/wiki';

/**
 * Service for handling wiki-related API calls
 */
export class WikiService {
  /**
   * Fetch wiki structure from the server cache
   */
  static async getWikiCache(
    owner: string,
    repo: string,
    repoType: string,
    language: string
  ): Promise<{ wikiStructure: WikiStructure; generatedPages: Record<string, WikiPage> } | null> {
    try {
      const response = await fetch(
        `/api/wiki_cache?owner=${encodeURIComponent(owner)}&repo=${encodeURIComponent(
          repo
        )}&repo_type=${encodeURIComponent(repoType)}&language=${encodeURIComponent(language)}`,
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch wiki cache: ${response.statusText}`);
      }

      const data = await response.json();
      if (!data) return null;

      return {
        wikiStructure: data.structure,
        generatedPages: data.pages,
      };
    } catch (error) {
      console.error('Error fetching wiki cache:', error);
      return null;
    }
  }

  /**
   * Save wiki structure to the server cache
   */
  static async saveWikiCache(
    owner: string,
    repo: string,
    repoType: string,
    language: string,
    wikiStructure: WikiStructure,
    generatedPages: Record<string, WikiPage>
  ): Promise<boolean> {
    try {
      const response = await fetch('/api/wiki_cache', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          owner,
          repo,
          repo_type: repoType,
          language,
          structure: wikiStructure,
          pages: generatedPages,
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to save wiki cache: ${response.statusText}`);
      }

      return true;
    } catch (error) {
      console.error('Error saving wiki cache:', error);
      return false;
    }
  }

  /**
   * Generate wiki structure for a repository
   */
  static async generateWikiStructure(
    repoInfo: RepoInfo,
    language: string,
    provider: string,
    model: string,
    isCustomModel: boolean,
    customModel: string,
    excludedDirs: string,
    excludedFiles: string
  ): Promise<WikiStructure> {
    try {
      const response = await fetch('/api/wiki/structure', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          repoInfo,
          language,
          provider,
          model: isCustomModel ? customModel : model,
          excludedDirs,
          excludedFiles,
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to generate wiki structure: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error generating wiki structure:', error);
      throw error;
    }
  }

  /**
   * Generate content for a wiki page
   */
  static async generatePageContent(
    repoInfo: RepoInfo,
    page: WikiPage,
    language: string,
    provider: string,
    model: string,
    isCustomModel: boolean,
    customModel: string
  ): Promise<string> {
    try {
      const response = await fetch('/api/wiki/page', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          repoInfo,
          page,
          language,
          provider,
          model: isCustomModel ? customModel : model,
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to generate page content: ${response.statusText}`);
      }

      const data = await response.json();
      return data.content;
    } catch (error) {
      console.error('Error generating page content:', error);
      throw error;
    }
  }

  /**
   * Export wiki as JSON or Markdown
   */
  static async exportWiki(
    repoUrl: string,
    pages: WikiPage[],
    format: 'json' | 'markdown'
  ): Promise<Blob> {
    try {
      const response = await fetch('/export/wiki', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          repo_url: repoUrl,
          pages,
          format,
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to export wiki: ${response.statusText}`);
      }

      return await response.blob();
    } catch (error) {
      console.error('Error exporting wiki:', error);
      throw error;
    }
  }
}
