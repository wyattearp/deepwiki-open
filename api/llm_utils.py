import logging
import os
import google.generativeai as genai
from adalflow.components.model_client.ollama_client import OllamaClient
from adalflow.core.types import ModelType
from api.openai_client import OpenAIClient
from api.openrouter_client import OpenRouterClient

# Get a logger for this module
logger = logging.getLogger(__name__)

async def call_llm_provider(prompt: str, provider: str, model_name: str, model_config: dict) -> str:
    """
    Call the appropriate LLM provider based on the provider name.
    
    Args:
        prompt: The prompt to send to the LLM
        provider: The provider to use (ollama, openrouter, openai, google)
        model_name: The model name to use
        model_config: The model configuration
        
    Returns:
        The generated text
    """
    try:
        if provider == "ollama":
            model = OllamaClient()
            model_kwargs = {
                "model": model_name,
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
            return response.text
            
        elif provider == "openrouter":
            # Check if OpenRouter API key is set
            if not os.environ.get("OPENROUTER_API_KEY"):
                logger.warning("OPENROUTER_API_KEY environment variable is not set, but continuing with request")
                
            model = OpenRouterClient()
            model_kwargs = {
                "model": model_name,
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
            return response.text
            
        elif provider == "openai":
            # Check if an API key is set for Openai
            if not os.environ.get("OPENAI_API_KEY"):
                logger.warning("OPENAI_API_KEY environment variable is not set, but continuing with request")
                
            model = OpenAIClient()
            model_kwargs = {
                "model": model_name,
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
            return response.text
            
        else:  # Default to Google
            # Initialize Google Generative AI model
            model = genai.GenerativeModel(
                model_name=model_config["model"],
                generation_config={
                    "temperature": model_config["temperature"],
                    "top_p": model_config["top_p"],
                    "top_k": model_config["top_k"]
                }
            )
            
            response = model.generate_content(prompt)
            return response.text
            
    except Exception as e:
        logger.error(f"Error calling LLM provider {provider}: {str(e)}")
        return f"Error generating content: {str(e)}"
