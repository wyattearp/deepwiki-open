/**
 * Represents a section in the wiki structure
 */
export interface WikiSection {
  id: string;
  title: string;
  pages: string[];
  subsections?: string[];
}

/**
 * Represents a page in the wiki structure
 */
export interface WikiPage {
  id: string;
  title: string;
  content: string;
  filePaths: string[];
  importance: 'high' | 'medium' | 'low';
  relatedPages: string[];
  parentId?: string;
  isSection?: boolean;
  children?: string[];
}

/**
 * Represents the overall structure of the wiki
 */
export interface WikiStructure {
  id: string;
  title: string;
  description: string;
  pages: WikiPage[];
  sections: WikiSection[];
  rootSections: string[];
}

/**
 * Represents a request to generate wiki structure
 */
export interface GenerateWikiStructureRequest {
  repoInfo: {
    owner: string;
    repo: string;
    type: string;
    token: string | null;
    localPath: string | null;
    repoUrl: string | null;
  };
  language: string;
  provider: string;
  model: string;
  excludedDirs: string;
  excludedFiles: string;
}

/**
 * Represents a request to generate wiki page content
 */
export interface GenerateWikiPageRequest {
  repoInfo: {
    owner: string;
    repo: string;
    type: string;
    token: string | null;
    localPath: string | null;
    repoUrl: string | null;
  };
  page: WikiPage;
  language: string;
  provider: string;
  model: string;
}

/**
 * Represents a response from generating wiki page content
 */
export interface GenerateWikiPageResponse {
  content: string;
}

/**
 * Represents a request to export wiki content
 */
export interface ExportWikiRequest {
  repo_url: string;
  pages: WikiPage[];
  format: 'json' | 'markdown';
}
