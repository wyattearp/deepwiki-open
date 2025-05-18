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
                    "temperature": model_config.get("temperature", 0.7),
                    "top_p": model_config.get("top_p", 0.95),
                    "num_ctx": model_config.get("num_ctx", 4096)
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
                logger.error("OPENROUTER_API_KEY environment variable is not set")
                return "Error: OpenRouter API key is required but not set in the environment. Please configure the API key and try again."

            model = OpenRouterClient()
            model_kwargs = {
                "model": model_name,
                "stream": False,
                "temperature": model_config.get("temperature", 0.7),
                "top_p": model_config.get("top_p", 0.95)
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
                logger.error("OPENAI_API_KEY environment variable is not set")
                return "Error: OpenAI API key is required but not set in the environment. Please configure the API key and try again."

            model = OpenAIClient()
            model_kwargs = {
                "model": model_name,
                "stream": False,
                "temperature": model_config.get("temperature", 0.7),
                "top_p": model_config.get("top_p", 0.95)
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
                model_name=model_name,  # Use the model_name parameter for consistency
                generation_config={
                    "temperature": model_config.get("temperature", 0.7),
                    "top_p": model_config.get("top_p", 0.95),
                    "top_k": model_config.get("top_k", 40)
                }
            )

            response = model.generate_content(prompt)
            return response.text

    except Exception as e:
        logger.error(f"Error calling LLM provider {provider}: {str(e)}")
        return f"Error generating content: {str(e)}"
