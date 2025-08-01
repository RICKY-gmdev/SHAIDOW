# tools.py

import os
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mistralai import ChatMistralAI
from langchain_core.tools import tool
from langchain_community.llms import Replicate



try:
    claude_sonnet = ChatAnthropic(model="claude-3-opus-20240229", temperature=0)
    mistral_large = ChatMistralAI(model="mistral-large-latest", temperature=0)
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
    Use this tool for complex reasoning, creative writing, and generating code.
    It is particularly strong at following detailed instructions and producing structured output like JSON or Python code.
    For example: 'write a python function to sort a list' or 'compose a short poem about the sea'.
    """
    print("--- INVOKING CLAUDE TOOL ---")
    try:
        response = claude_sonnet.invoke(query)
        return response.content
    except Exception as e:
        return f"Error invoking Claude tool: {e}"

@tool
def mistral_tool(query: str) -> str:
    """
    Use this tool for fast and concise information retrieval, summarization, or answering general knowledge questions.
    It is highly efficient for tasks that require synthesizing information from a broad context.
    For example: 'what is the capital of France?' or 'summarize the theory of relativity'.
    """
    print("--- INVOKING MISTRAL TOOL ---")
    try:
        response = mistral_large.invoke(query)
        return response.content
    except Exception as e:
        return f"Error invoking Mistral tool: {e}"

@tool
def stable_diffusion_tool(prompt: str) -> str:
    """
    Use this tool ONLY when the user explicitly asks to generate, create, or draw an image.
    The input should be a descriptive text prompt of the image to be created.
    This tool returns a URL to the generated image.
    """
    print("--- INVOKING STABLE DIFFUSION TOOL ---")
    try:
       
        output = replicate_stable_diffusion.invoke(prompt)
        
        return f"Image generated successfully: {output}"
    except Exception as e:
        return f"Error invoking Stable Diffusion tool: {e}. The model may be unavailable."

@tool
def general_chat_tool(query: str) -> str:
    """
    Use this tool for general conversation, greetings, or as a fallback if no other tool is suitable for the user's request.
    This is the default tool for chit-chat and open-ended questions.
    """
    print("--- INVOKING GENERAL CHAT (GEMINI) TOOL ---")
    try:
        response = gemini_flash.invoke(query)
        return response.content
    except Exception as e:
        return f"Error invoking General Chat tool: {e}"


all_tools = [claude_tool, mistral_tool, stable_diffusion_tool, general_chat_tool]