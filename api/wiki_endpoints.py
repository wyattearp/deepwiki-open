import os
import logging
from fastapi import HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import google.generativeai as genai
from api.data_pipeline import count_tokens, get_file_content
from api.config import get_model_config
from api.llm_utils import call_llm_provider

# Get a logger for this module
logger = logging.getLogger(__name__)

# --- Pydantic Models ---
class WikiPageRequest(BaseModel):
    """
    Model for requesting wiki page generation.
    """
    repo_url: str = Field(..., description="URL of the repository")
    page: Dict[str, Any] = Field(..., description="Page information")
    language: str = Field("en", description="Language for the content")
    provider: str = Field("google", description="AI provider to use")
    model: str = Field("gemini-1.5-pro", description="Model to use")
    token: Optional[str] = Field(None, description="Personal access token for private repositories")
    type: Optional[str] = Field("github", description="Type of repository (e.g., 'github', 'gitlab', 'bitbucket')")

class WikiStructureRequest(BaseModel):
    """
    Model for requesting wiki structure generation.
    """
    repo_url: str = Field(..., description="URL of the repository")
    language: str = Field("en", description="Language for the content")
    provider: str = Field("google", description="AI provider to use")
    model: str = Field("gemini-1.5-pro", description="Model to use")
    excluded_dirs: List[str] = Field([], description="Directories to exclude")
    excluded_files: List[str] = Field([], description="Files to exclude")
    token: Optional[str] = Field(None, description="Personal access token for private repositories")
    type: Optional[str] = Field("github", description="Type of repository (e.g., 'github', 'gitlab', 'bitbucket')")

class WikiPageResponse(BaseModel):
    """
    Model for wiki page generation response.
    """
    content: str = Field(..., description="Generated page content")

class WikiStructureResponse(BaseModel):
    """
    Model for wiki structure generation response.
    """
    id: str = Field(..., description="Wiki structure ID")
    title: str = Field(..., description="Wiki title")
    description: str = Field(..., description="Wiki description")
    pages: List[Dict[str, Any]] = Field(..., description="Wiki pages")
    sections: List[Dict[str, Any]] = Field(..., description="Wiki sections")
    rootSections: List[str] = Field(..., description="Root sections")

# --- Helper Functions ---
def get_language_name(language_code: str) -> str:
    """
    Get the full language name from a language code.
    """
    language_map = {
        "en": "English",
        "fr": "French",
        "es": "Spanish",
        "de": "German",
        "it": "Italian",
        "pt": "Portuguese",
        "ru": "Russian",
        "zh": "Chinese",
        "ja": "Japanese",
        "ko": "Korean",
        # Add more languages as needed
    }
    return language_map.get(language_code, "English")

async def generate_wiki_page(request: WikiPageRequest) -> WikiPageResponse:
    """
    Generate content for a wiki page.
    """
    try:
        # Get model configuration
        model_config = get_model_config(request.provider, request.model)

        # Get language name
        language_name = get_language_name(request.language)

        # Prepare the prompt
        system_prompt = f"""You are an expert documentation generator for code repositories.
You will be given information about a page to generate for a wiki about a code repository.
Your task is to create comprehensive, well-structured content for this page.

IMPORTANT: You MUST respond in {language_name} language.

The page you need to create is about: "{request.page['title']}"

You should use the following source files as reference:
{', '.join(request.page['filePaths'])}

Please create detailed, accurate content that explains the purpose, functionality, and implementation details
related to this topic. Include code examples where appropriate, and make sure to structure the content
with clear headings and sections.
"""

        # Get file content for the relevant files
        file_contents = []
        missing_files = []

        for file_path in request.page['filePaths']:
            try:
                content = await get_file_content(
                    request.repo_url,
                    file_path,
                    token=request.token,
                    repo_type=request.type
                )
                if content:
                    file_contents.append(f"File: {file_path}\n```\n{content}\n```")
                else:
                    missing_files.append(file_path)
                    logger.warning(f"No content returned for file {file_path}")
            except Exception as e:
                missing_files.append(file_path)
                logger.warning(f"Error getting content for file {file_path}: {str(e)}")

        # Check if we have enough files
        if len(file_contents) == 0:
            error_msg = f"Failed to retrieve content for any of the specified files: {', '.join(request.page['filePaths'])}"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)

        # Add a note about missing files
        if missing_files:
            missing_files_note = f"Note: The following files could not be retrieved: {', '.join(missing_files)}"
            file_contents.append(missing_files_note)

        # Combine file contents
        context = "\n\n".join(file_contents)

        # Create the full prompt
        prompt = f"{system_prompt}\n\nHere are the relevant source files:\n\n{context}"

        # Check token count and truncate if necessary
        token_count = count_tokens(prompt)
        max_tokens = model_config.get("max_input_tokens", 8000)

        if token_count > max_tokens:
            logger.warning(f"Prompt exceeds token limit ({token_count} > {max_tokens}). Truncating...")

            # More sophisticated truncation strategy
            # 1. Reserve tokens for system prompt and other parts
            system_prompt_tokens = count_tokens(system_prompt)
            reserved_tokens = system_prompt_tokens + 200  # Extra tokens for formatting
            available_tokens = max_tokens - reserved_tokens

            # 2. Split context into files and truncate each file if needed
            file_contents_split = context.split("\n\nFile: ")
            header = file_contents_split[0] if file_contents_split else ""
            files = ["File: " + f for f in file_contents_split[1:]] if len(file_contents_split) > 1 else []

            # 3. Calculate tokens per file
            file_tokens = [count_tokens(f) for f in files]
            total_file_tokens = sum(file_tokens)

            # 4. If we need to truncate, do it proportionally per file
            if total_file_tokens > available_tokens:
                # Allocate tokens proportionally to each file based on its size
                truncated_files = []
                for i, file_content in enumerate(files):
                    # Calculate proportion of tokens for this file
                    file_proportion = file_tokens[i] / total_file_tokens
                    file_max_tokens = int(available_tokens * file_proportion)

                    # If file needs truncation
                    if count_tokens(file_content) > file_max_tokens:
                        # Try to truncate at a natural boundary like a function or class
                        lines = file_content.split("\n")
                        truncated_lines = []
                        current_tokens = 0

                        for line in lines:
                            line_tokens = count_tokens(line)
                            if current_tokens + line_tokens > file_max_tokens:
                                # We've reached our limit
                                break
                            truncated_lines.append(line)
                            current_tokens += line_tokens

                        # Join the lines back together
                        truncated_file = "\n".join(truncated_lines)
                        truncated_file += "\n\n...[truncated due to token limit]"
                        truncated_files.append(truncated_file)
                    else:
                        # No truncation needed for this file
                        truncated_files.append(file_content)

                # Reconstruct the context
                context = header + "\n\n" + "\n\n".join(truncated_files)

            # Rebuild the prompt
            prompt = f"{system_prompt}\n\nHere are the relevant source files (some may be truncated due to token limits):\n\n{context}"

        # Generate content using the LLM provider
        content = await call_llm_provider(
            prompt=prompt,
            provider=request.provider,
            model_name=request.model,
            model_config=model_config
        )

        return WikiPageResponse(content=content)

    except Exception as e:
        logger.error(f"Error generating wiki page: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating wiki page: {str(e)}")

async def generate_wiki_structure(request: WikiStructureRequest) -> WikiStructureResponse:
    """
    Generate the structure for a wiki.
    """
    try:
        # Get model configuration
        model_config = get_model_config(request.provider, request.model)

        # Get language name
        language_name = get_language_name(request.language)

        # Prepare the prompt
        system_prompt = f"""You are an expert documentation generator for code repositories.
Your task is to analyze a code repository and create a structured wiki outline.

IMPORTANT: You MUST respond in {language_name} language.

The repository you need to analyze is: {request.repo_url}

Please create a comprehensive wiki structure with the following:
1. An overall title for the wiki
2. A brief description of the repository
3. Sections that logically organize the content
4. Pages within each section that cover specific topics
5. For each page, include:
   - A title
   - A brief description
   - Importance level (high, medium, low)
   - Relevant file paths
   - Related pages

Your response should be in the following XML format:

<wiki_structure>
  <title>[Overall title for the wiki]</title>
  <description>[Brief description of the repository]</description>
  <sections>
    <section id="section-1">
      <title>[Section title]</title>
      <pages>
        <page_ref>page-1</page_ref>
        <page_ref>page-2</page_ref>
      </pages>
      <subsections>
        <section_ref>section-2</section_ref>
      </subsections>
    </section>
    <!-- More sections as needed -->
  </sections>
  <pages>
    <page id="page-1">
      <title>[Page title]</title>
      <description>[Brief description of what this page will cover]</description>
      <importance>high|medium|low</importance>
      <relevant_files>
        <file_path>[Path to a relevant file]</file_path>
        <!-- More file paths as needed -->
      </relevant_files>
      <related_pages>
        <related>page-2</related>
        <!-- More related page IDs as needed -->
      </related_pages>
    </page>
    <!-- More pages as needed -->
  </pages>
</wiki_structure>
"""

        # Get file tree from the repository
        try:
            # For GitHub repositories
            if request.type == "github" or request.type is None:
                from api.data_pipeline import get_github_file_tree
                file_tree, _ = await get_github_file_tree(
                    request.repo_url,
                    token=request.token
                )
            # For GitLab repositories
            elif request.type == "gitlab":
                from api.data_pipeline import get_gitlab_file_tree
                file_tree, _ = await get_gitlab_file_tree(
                    request.repo_url,
                    token=request.token
                )
            # For Bitbucket repositories
            elif request.type == "bitbucket":
                from api.data_pipeline import get_bitbucket_file_tree
                file_tree, _ = await get_bitbucket_file_tree(
                    request.repo_url,
                    token=request.token
                )
            # For local repositories
            elif request.type == "local":
                from api.data_pipeline import get_local_file_tree
                file_tree, _ = await get_local_file_tree(request.repo_url)
            else:
                file_tree = "Unknown repository type"
                logger.warning(f"Unknown repository type: {request.type}")
        except Exception as e:
            logger.error(f"Error getting file tree: {str(e)}")
            file_tree = f"Error getting file tree: {str(e)}"

        # Create the full prompt
        prompt = f"{system_prompt}\n\nHere is the file tree for the repository:\n\n{file_tree}"

        # Check token count and truncate if necessary
        token_count = count_tokens(prompt)
        max_tokens = model_config.get("max_input_tokens", 8000)

        if token_count > max_tokens:
            logger.warning(f"Prompt exceeds token limit ({token_count} > {max_tokens}). Truncating...")

            # More sophisticated truncation strategy for file tree
            # 1. Reserve tokens for system prompt
            system_prompt_tokens = count_tokens(system_prompt)
            reserved_tokens = system_prompt_tokens + 200  # Extra tokens for formatting
            available_tokens = max_tokens - reserved_tokens

            # 2. If file tree needs truncation, prioritize top-level directories
            if count_tokens(file_tree) > available_tokens:
                # Split file tree into lines
                file_tree_lines = file_tree.split('\n')

                # Identify depth of each line (by counting leading spaces/indentation)
                def get_line_depth(line):
                    return len(line) - len(line.lstrip())

                # Sort lines by depth (keep directory structure intact)
                lines_with_depth = [(get_line_depth(line), i, line) for i, line in enumerate(file_tree_lines)]

                # Sort by depth first, then by original order to maintain structure
                lines_with_depth.sort(key=lambda x: (x[0], x[1]))

                # Take lines until we reach token limit
                truncated_lines = []
                current_tokens = 0

                # Always include the first few lines (repository root)
                root_lines = file_tree_lines[:min(5, len(file_tree_lines))]
                for line in root_lines:
                    truncated_lines.append(line)
                    current_tokens += count_tokens(line)

                # Then add lines prioritizing lower depth
                for depth, _, line in lines_with_depth:
                    if line in root_lines:  # Skip lines we've already added
                        continue

                    line_tokens = count_tokens(line)
                    if current_tokens + line_tokens > available_tokens * 0.95:  # Leave some margin
                        break

                    truncated_lines.append(line)
                    current_tokens += line_tokens

                # Add a note about truncation
                truncated_lines.append("\n...[file tree truncated due to token limit]")

                # Reconstruct the file tree, maintaining original order
                original_indices = {line: i for i, line in enumerate(file_tree_lines)}
                truncated_lines.sort(key=lambda x: original_indices.get(x, float('inf')))

                file_tree = '\n'.join(truncated_lines)

            # Rebuild the prompt
            prompt = f"{system_prompt}\n\nHere is the file tree for the repository (truncated to focus on main directories):\n\n{file_tree}"

        # Generate content using the LLM provider
        content = await call_llm_provider(
            prompt=prompt,
            provider=request.provider,
            model_name=request.model,
            model_config=model_config
        )

        # Parse the XML response to extract the wiki structure
        try:
            import re
            import xml.etree.ElementTree as ET

            # Extract the XML content from the response
            xml_match = re.search(r'<wiki_structure>.*?</wiki_structure>', content, re.DOTALL)

            if not xml_match:
                logger.warning("No wiki_structure XML found in the response")
                # Log the problematic LLM output for debugging
                logger.debug(f"LLM response without XML structure: {content[:500]}...")
                # Fallback structure if no XML is found
                structure = {
                    "id": "wiki-1",
                    "title": "Repository Wiki",
                    "description": "A comprehensive wiki for the repository",
                    "pages": [
                        {
                            "id": "page-1",
                            "title": "Introduction",
                            "content": "",
                            "filePaths": ["README.md"],
                            "importance": "high",
                            "relatedPages": []
                        }
                    ],
                    "sections": [
                        {
                            "id": "section-1",
                            "title": "Getting Started",
                            "pages": ["page-1"],
                            "subsections": []
                        }
                    ],
                    "rootSections": ["section-1"]
                }
            else:
                xml_content = xml_match.group(0)

                # Parse the XML
                root = ET.fromstring(xml_content)

                # Extract title and description
                title_elem = root.find('title')
                desc_elem = root.find('description')

                title = title_elem.text if title_elem is not None and title_elem.text else "Repository Wiki"
                description = desc_elem.text if desc_elem is not None and desc_elem.text else "A comprehensive wiki for the repository"

                # Extract pages
                pages = []
                pages_elem = root.find('pages')
                if pages_elem is not None:
                    for page_elem in pages_elem.findall('page'):
                        page_id = page_elem.get('id', f"page-{len(pages)+1}")

                        # Extract page title
                        page_title_elem = page_elem.find('title')
                        page_title = page_title_elem.text if page_title_elem is not None and page_title_elem.text else "Untitled Page"

                        # Extract importance
                        importance_elem = page_elem.find('importance')
                        importance = importance_elem.text if importance_elem is not None and importance_elem.text in ["high", "medium", "low"] else "medium"

                        # Extract file paths
                        file_paths = []
                        relevant_files_elem = page_elem.find('relevant_files')
                        if relevant_files_elem is not None:
                            for file_path_elem in relevant_files_elem.findall('file_path'):
                                if file_path_elem.text:
                                    file_paths.append(file_path_elem.text)

                        # Extract related pages
                        related_pages = []
                        related_pages_elem = page_elem.find('related_pages')
                        if related_pages_elem is not None:
                            for related_elem in related_pages_elem.findall('related'):
                                if related_elem.text:
                                    related_pages.append(related_elem.text)

                        # Create page object
                        pages.append({
                            "id": page_id,
                            "title": page_title,
                            "content": "",  # Content will be generated separately
                            "filePaths": file_paths,
                            "importance": importance,
                            "relatedPages": related_pages
                        })

                # Extract sections
                sections = []
                root_sections = []
                sections_elem = root.find('sections')
                if sections_elem is not None:
                    for section_elem in sections_elem.findall('section'):
                        section_id = section_elem.get('id', f"section-{len(sections)+1}")

                        # Extract section title
                        section_title_elem = section_elem.find('title')
                        section_title = section_title_elem.text if section_title_elem is not None and section_title_elem.text else "Untitled Section"

                        # Extract pages in this section
                        section_pages = []
                        pages_elem = section_elem.find('pages')
                        if pages_elem is not None:
                            for page_ref_elem in pages_elem.findall('page_ref'):
                                if page_ref_elem.text:
                                    section_pages.append(page_ref_elem.text)

                        # Extract subsections
                        subsections = []
                        subsections_elem = section_elem.find('subsections')
                        if subsections_elem is not None:
                            for section_ref_elem in subsections_elem.findall('section_ref'):
                                if section_ref_elem.text:
                                    subsections.append(section_ref_elem.text)

                        # Create section object
                        sections.append({
                            "id": section_id,
                            "title": section_title,
                            "pages": section_pages,
                            "subsections": subsections
                        })

                        # Add to root sections if it's a top-level section
                        # This is a simplification - in a real implementation, you might want to check
                        # if this section is referenced as a subsection by any other section
                        root_sections.append(section_id)

                # Create the structure object
                structure = {
                    "id": "wiki-1",
                    "title": title,
                    "description": description,
                    "pages": pages,
                    "sections": sections,
                    "rootSections": root_sections
                }
        except Exception as e:
            logger.error(f"Error parsing wiki structure XML: {str(e)}")
            # Log the problematic XML content for debugging
            if 'xml_content' in locals():
                logger.debug(f"Problematic XML content: {xml_content[:500]}...")
            else:
                logger.debug(f"No XML content extracted from response: {content[:500]}...")
            # Fallback structure if parsing fails
            structure = {
                "id": "wiki-1",
                "title": "Repository Wiki",
                "description": "A comprehensive wiki for the repository",
                "pages": [
                    {
                        "id": "page-1",
                        "title": "Introduction",
                        "content": "",
                        "filePaths": ["README.md"],
                        "importance": "high",
                        "relatedPages": []
                    }
                ],
                "sections": [
                    {
                        "id": "section-1",
                        "title": "Getting Started",
                        "pages": ["page-1"],
                        "subsections": []
                    }
                ],
                "rootSections": ["section-1"]
            }

        return WikiStructureResponse(**structure)

    except Exception as e:
        logger.error(f"Error generating wiki structure: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating wiki structure: {str(e)}")
