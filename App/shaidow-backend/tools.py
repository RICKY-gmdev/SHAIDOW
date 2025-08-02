import os
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mistralai import ChatMistralAI
from langchain_core.tools import tool
from langchain_community.llms import Replicate
import re # Import the regular expression module

# --- Model initializations remain the same ---
try:
    claude_sonnet = ChatAnthropic(model="claude-3-opus-20240229", temperature=0)
    mistral_large = ChatMistralAI(
    model="mistral-large-latest",
    temperature=0,
    api_key=os.getenv("MISTRAL_API_KEY") # Explicitly pass the API key
)
    gemini_flash = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.7)
    
    stable_diffusion_model_id = "stability-ai/stable-diffusion:ac732df83cea7fff18b8472768c88ad041fa750ff7682a21affe81863cbe77e4"
    replicate_stable_diffusion = Replicate(
        model=stable_diffusion_model_id,
        replicate_api_token=os.getenv("REPLICATE_API_TOKEN")
    )
except Exception as e:
    print(f"Warning: Failed to initialize one or more tool models. Check API keys. Error: {e}")

@tool
def claude_tool(query: str) -> str:
    """
    Use for complex reasoning, creative tasks (writing poems, stories, code), and following detailed instructions.
    """
    print("--- INVOKING CLAUDE TOOL ---")
    try:
        response = claude_sonnet.invoke(query)
        # Ensure we return a clean string
        return response.content.strip()
    except Exception as e:
        return f"Error invoking Claude tool: {e}"

@tool
def mistral_tool(query: str) -> str:
    """
    Use for quick, factual answers, summarization, and general knowledge questions.
    """
    print("--- INVOKING MISTRAL TOOL ---")
    try:
        response = mistral_large.invoke(query)
        # Ensure we return a clean string
        return response.content.strip()
    except Exception as e:
        return f"Error invoking Mistral tool: {e}"

@tool
def stable_diffusion_tool(prompt: str) -> str:
    """
    Use this tool ONLY when the user explicitly asks to generate, create, or draw an image, picture, or photo.
    """
    print("--- INVOKING STABLE DIFFUSION TOOL ---")
    try:
        # The output from Replicate is often a list of URLs, so we handle that
        output = replicate_stable_diffusion.invoke(prompt)
        # Use regex to find the URL, which is more robust
        url_match = re.search(r'https?://\S+', str(output))
        if url_match:
            image_url = url_match.group(0)
            # Return a structured, predictable string
            return f"IMAGE_URL::{image_url}"
        else:
            return "Error: Could not extract image URL from the model's response."
            
    except Exception as e:
        return f"Error invoking Stable Diffusion tool: {e}. The model may be unavailable."

all_tools = [claude_tool, mistral_tool, stable_diffusion_tool]