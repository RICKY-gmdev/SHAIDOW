# tools.py
import os
import requests
import base64
from typing import Any, List
from langchain_core.tools import tool
from langchain_core.messages import BaseMessage
from langchain_anthropic import ChatAnthropic
from langchain_mistralai import ChatMistralAI


def _claude(): return ChatAnthropic(model="claude-3-opus-20240229", temperature=0.1)
def _mistral(): return ChatMistralAI(model="mistral-large-latest", temperature=0, api_key=os.getenv("MISTRAL_API_KEY"))



def _extract_content(resp: Any) -> str:
    if resp is None: return "No content."
    if isinstance(resp, str): return resp.strip() or "No content."
    if isinstance(resp, BaseMessage):
        c = resp.content
        if isinstance(c, list):
            parts: List[str] = []
            for p in c:
                if isinstance(p, dict):
                    txt = p.get("text")
                    if txt: parts.append(str(txt))
                elif isinstance(p, str): parts.append(p)
            c = "\n".join(parts)
        if isinstance(c, str): c = c.strip()
        return c or "No content."
    if isinstance(resp, list):
        for item in resp:
            extracted = _extract_content(item)
            if extracted and extracted != "No content.": return extracted
        return "No content."
    return str(resp)[:4000] or "No content."


@tool
def claude_tool(query: str) -> str:
    """Complex reasoning, creative or multi-step tasks."""
    try: return _extract_content(_claude().invoke(query))
    except Exception as e: return f"Claude error: {e}"

@tool
def mistral_tool(query: str) -> str:
    """Use for quick, factual answers, summarization, and general knowledge questions."""
    print("--- INVOKING MISTRAL TOOL ---")
    try:
        response = _mistral().invoke(query)
        return _extract_content(response)
    except Exception as e:
        return f"Error invoking Mistral tool: {e}"



@tool
def search_for_image_tool(query: str) -> str:
    """
    Use this tool to search for a real, embeddable image.
    Provide a descriptive search query.
    Returns a URL to a relevant image found online.
    """
    print(f"--- Searching for an image with Pexels API for query: '{query}' ---")
    try:
        api_key = os.getenv("PEXELS_API_KEY")
        if not api_key:
            return "Error: PEXELS_API_KEY environment variable not set."

        headers = {"Authorization": api_key}
        url = f"https://api.pexels.com/v1/search?query={query}&per_page=1"
        
        response = requests.get(url, headers=headers)
        response.raise_for_status() 
        
        data = response.json()

        if data["photos"]:
            
            image_url = data["photos"][0]["src"]["large"] 
            print(f"--- Pexels image search success. URL: {image_url} ---")
            return f"IMAGE_URL::{image_url}"
        else:
            return "Error: Pexels API did not find any images for this query."

    except Exception as e:
        print(f"--- Pexels search Error: {e} ---")
        return f"Pexels search error: {e}"



@tool
def generate_image_tool(prompt: str) -> str:
    """
    Use this tool to create or generate a completely new image from a text description.
    Use it for requests like 'draw', 'create', 'generate an artwork of', or for fictional or imaginative scenes.
    Returns the generated image data directly.
    """
    print(f"--- Calling Stability AI v2beta API to generate image for prompt: '{prompt}' ---")
    
    api_url = "https://api.stability.ai/v2beta/stable-image/generate/sd3"
    api_key = os.getenv("STABILITY_API_KEY")
    if not api_key: return "Error: STABILITY_API_KEY environment variable not set."
    headers = {"authorization": f"Bearer {api_key}", "accept": "image/*"}
    files = {'prompt': (None, prompt), 'model': (None, 'sd3.5-flash'), 'output_format': (None, 'png')}
    try:
        response = requests.post(api_url, headers=headers, files=files)
        if response.status_code == 200:
            base64_image = base64.b64encode(response.content).decode('utf-8')
            data_uri = f"data:image/png;base64,{base64_image}"
            print("--- Image generation success. Returning Base64 data URI. ---")
            return f"IMAGE_DATA::{data_uri}"
        else:
            error_details = response.json().get('errors', [str(response.text)])
            print(f"--- Stability AI Error: {response.status_code} - {error_details[0]} ---")
            return f"Stability AI API Error: {response.status_code} - {error_details[0]}"
    except Exception as e:
        print(f"--- Stability AI Request Error: {e} ---")
        return f"Stability AI request error: {e}"



all_tools = [claude_tool, mistral_tool, search_for_image_tool, generate_image_tool]