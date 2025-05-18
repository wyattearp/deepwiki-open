import os
import logging
from fastapi import HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import google.generativeai as genai
from api.data_pipeline import count_tokens, get_file_content
from api.config import get_model_config
from api.openai_client import OpenAIClient
from api.openrouter_client import OpenRouterClient
from adalflow.components.model_client.ollama_client import OllamaClient
from adalflow.core.types import ModelType

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
            except Exception as e:
                logger.warning(f"Error getting content for file {file_path}: {str(e)}")
        
        # Combine file contents
        context = "\n\n".join(file_contents)
        
        # Create the full prompt
        prompt = f"{system_prompt}\n\nHere are the relevant source files:\n\n{context}"
        
        # Check token count and truncate if necessary
        token_count = count_tokens(prompt)
        max_tokens = model_config.get("max_input_tokens", 8000)
        
        if token_count > max_tokens:
            logger.warning(f"Prompt exceeds token limit ({token_count} > {max_tokens}). Truncating...")
            # Simple truncation strategy - in a real implementation, you might want something more sophisticated
            truncation_ratio = max_tokens / token_count
            context_tokens = int(len(context) * truncation_ratio * 0.9)  # Leave some room for the system prompt
            context = context[:context_tokens] + "...[truncated due to token limit]"
            prompt = f"{system_prompt}\n\nHere are the relevant source files (truncated):\n\n{context}"
        
        # Generate content based on the provider
        if request.provider == "ollama":
            model = OllamaClient()
            model_kwargs = {
                "model": request.model,
                "stream": False,
                "options": {
                    "temperature": model_config["temperature"],
                    "top_p": model_config["top_p"],
                    "num_ctx": model_config["num_ctx"]
                }
            }
            
            api_kwargs = model.convert_inputs_to_api_kwargs(
                input=prompt,
                model_kwargs=model_kwargs,
                model_type=ModelType.LLM
            )
            
            response = model.generate(**api_kwargs)
            content = response.text
            
        elif request.provider == "openrouter":
            model = OpenRouterClient()
            model_kwargs = {
                "model": request.model,
                "stream": False,
                "temperature": model_config["temperature"],
                "top_p": model_config["top_p"]
            }
            
            api_kwargs = model.convert_inputs_to_api_kwargs(
                input=prompt,
                model_kwargs=model_kwargs,
                model_type=ModelType.LLM
            )
            
            response = model.generate(**api_kwargs)
            content = response.text
            
        elif request.provider == "openai":
            model = OpenAIClient()
            model_kwargs = {
                "model": request.model,
                "stream": False,
                "temperature": model_config["temperature"],
                "top_p": model_config["top_p"]
            }
            
            api_kwargs = model.convert_inputs_to_api_kwargs(
                input=prompt,
                model_kwargs=model_kwargs,
                model_type=ModelType.LLM
            )
            
            response = model.generate(**api_kwargs)
            content = response.text
            
        else:  # Default to Google
            model = genai.GenerativeModel(
                model_name=model_config["model"],
                generation_config={
                    "temperature": model_config["temperature"],
                    "top_p": model_config["top_p"],
                    "top_k": model_config["top_k"]
                }
            )
            
            response = model.generate_content(prompt)
            content = response.text
        
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

        # Get file tree
        # In a real implementation, you would get the file tree from the repository
        # For now, we'll use a placeholder
        file_tree = "This is a placeholder for the file tree"
        
        # Create the full prompt
        prompt = f"{system_prompt}\n\nHere is the file tree for the repository:\n\n{file_tree}"
        
        # Check token count and truncate if necessary
        token_count = count_tokens(prompt)
        max_tokens = model_config.get("max_input_tokens", 8000)
        
        if token_count > max_tokens:
            logger.warning(f"Prompt exceeds token limit ({token_count} > {max_tokens}). Truncating...")
            # Simple truncation strategy
            truncation_ratio = max_tokens / token_count
            file_tree_tokens = int(len(file_tree) * truncation_ratio * 0.9)
            file_tree = file_tree[:file_tree_tokens] + "...[truncated due to token limit]"
            prompt = f"{system_prompt}\n\nHere is the file tree for the repository (truncated):\n\n{file_tree}"
        
        # Generate content based on the provider
        if request.provider == "ollama":
            model = OllamaClient()
            model_kwargs = {
                "model": request.model,
                "stream": False,
                "options": {
                    "temperature": model_config["temperature"],
                    "top_p": model_config["top_p"],
                    "num_ctx": model_config["num_ctx"]
                }
            }
            
            api_kwargs = model.convert_inputs_to_api_kwargs(
                input=prompt,
                model_kwargs=model_kwargs,
                model_type=ModelType.LLM
            )
            
            response = model.generate(**api_kwargs)
            content = response.text
            
        elif request.provider == "openrouter":
            model = OpenRouterClient()
            model_kwargs = {
                "model": request.model,
                "stream": False,
                "temperature": model_config["temperature"],
                "top_p": model_config["top_p"]
            }
            
            api_kwargs = model.convert_inputs_to_api_kwargs(
                input=prompt,
                model_kwargs=model_kwargs,
                model_type=ModelType.LLM
            )
            
            response = model.generate(**api_kwargs)
            content = response.text
            
        elif request.provider == "openai":
            model = OpenAIClient()
            model_kwargs = {
                "model": request.model,
                "stream": False,
                "temperature": model_config["temperature"],
                "top_p": model_config["top_p"]
            }
            
            api_kwargs = model.convert_inputs_to_api_kwargs(
                input=prompt,
                model_kwargs=model_kwargs,
                model_type=ModelType.LLM
            )
            
            response = model.generate(**api_kwargs)
            content = response.text
            
        else:  # Default to Google
            model = genai.GenerativeModel(
                model_name=model_config["model"],
                generation_config={
                    "temperature": model_config["temperature"],
                    "top_p": model_config["top_p"],
                    "top_k": model_config["top_k"]
                }
            )
            
            response = model.generate_content(prompt)
            content = response.text
        
        # Parse the XML response to extract the wiki structure
        # In a real implementation, you would parse the XML and convert it to the expected format
        # For now, we'll return a placeholder structure
        
        # Placeholder structure
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
