#tools.py

import os
import re
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mistralai import ChatMistralAI
from langchain_core.tools import tool
from langchain_core.messages import BaseMessage
from langchain_community.llms import Replicate

# --- Model initializations ---
try:
    claude_sonnet = ChatAnthropic(model="claude-3-opus-20240229", temperature=0)
    mistral_large = ChatMistralAI(
        model="mistral-large-latest",
        temperature=0,
        api_key=os.getenv("MISTRAL_API_KEY")
    )
    gemini_flash = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.7)
    stable_diffusion_model_id = (
        "stability-ai/stable-diffusion:ac732df83cea7fff18b8472768c88ad041fa750ff7682a21affe81863cbe77e4"
    )
    replicate_stable_diffusion = Replicate(
        model=stable_diffusion_model_id,
        replicate_api_token=os.getenv("REPLICATE_API_TOKEN")
    )
except Exception as e:
    print(f"Warning: Failed to initialize one or more tool models. Error: {e}")

def _extract_content_from_response(response) -> str:
    """A helper function to robustly extract string content from various response types."""
    if isinstance(response, str):
        return response.strip()
    if isinstance(response, BaseMessage) and hasattr(response, 'content'):
        return response.content.strip() if response.content else ""
    # Handle cases where the response might be a list containing one message
    if isinstance(response, list) and response and isinstance(response, BaseMessage) and hasattr(response, 'content'):
        return response.content.strip() if response.content else ""
    return str(response)

# --- Claude Tool ---
@tool
def claude_tool(query: str) -> str:
    """Use for complex reasoning, creative tasks (writing poems, stories, code), and following detailed instructions."""
    print("--- INVOKING CLAUDE TOOL ---")
    try:
        response = claude_sonnet.invoke(query)
        return _extract_content_from_response(response)
    except Exception as e:
        return f"Error invoking Claude tool: {e}"

# --- Mistral Tool ---
@tool
def mistral_tool(query: str) -> str:
    """Use for quick, factual answers, summarization, and general knowledge questions."""
    print("--- INVOKING MISTRAL TOOL ---")
    try:
        response = mistral_large.invoke([("human", query)])
        return _extract_content_from_response(response)
    except Exception as e:
        return f"Error invoking Mistral tool: {e}"


# --- Stable Diffusion Tool ---
@tool
def stable_diffusion_tool(prompt: str) -> str:
    """Use this tool ONLY when the user explicitly asks to generate, create, or draw an image."""
    print("--- INVOKING STABLE DIFFUSION TOOL ---")
    try:
        output = replicate_stable_diffusion.invoke(prompt)
        if isinstance(output, list) and output:
            return f"IMAGE_URL::{output}"
        url_match = re.search(r'https?://\S+', str(output))
        return f"IMAGE_URL::{url_match.group(0)}" if url_match else "Error: No image URL found."
    except Exception as e:
        return f"Error invoking Stable Diffusion tool: {e}"

# Register all tools
all_tools = [claude_tool, mistral_tool, stable_diffusion_tool]