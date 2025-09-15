# tools.py

import os
import requests
import base64
from typing import Any, List
from langchain_core.tools import tool
from langchain_core.messages import BaseMessage
from langchain_mistralai import ChatMistralAI
import uuid

def _mistral(): 
    return ChatMistralAI(
        model="mistral-large-latest", 
        temperature=0, 
        api_key=os.getenv("MISTRAL_API_KEY")
    )

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

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

def _groq_chat(model: str, query: str, system_prompt: str = "You are a helpful assistant.") -> str:
    """Helper to call Groq chat completions API."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return "Error: GROQ_API_KEY not set."

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ],
        "temperature": 0.3,
        "max_tokens": 2048,   # bumped up for longer answers
    }

    try:
        resp = requests.post(GROQ_URL, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"Groq error: {e}"


# ------------------- TOOLS -------------------

@tool
def reasoning_tool(query: str) -> str:
    """General reasoning and versatile Q&A (Claude replacement)."""
    return _groq_chat(
        model="qwen/qwen3-32b",
        query=query,
        reasoning_effort="default",
        temperature=0.6,
        stream=True
    )





@tool
def coding_tool(query: str) -> str:
    """Use DeepSeek for coding, debugging, and clean code generation."""
    return _groq_chat("llama-3.1-8b-instant", query, "You are an expert coding assistant. Generate clean, working code.")

@tool
def mistral_tool(query: str) -> str:
    """Quick, factual answers, summaries, and general knowledge lookup."""
    print("--- INVOKING MISTRAL TOOL ---")
    try:
        response = _mistral().invoke(query)
        return _extract_content(response)
    except Exception as e:
        return f"Error invoking Mistral tool: {e}"

@tool
def search_for_image_tool(query: str) -> str:
    """Search for a real image using the Pexels API and return a URL."""
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
            return f"IMAGE_URL::{image_url}"
        else:
            return "No images found."
    except Exception as e:
        return f"Pexels search error: {e}"

@tool
def generate_image_tool(prompt: str) -> str:
    """
    Use this tool to create or generate a completely new image from a text description.
    Saves the image to a file and returns a URL to it.
    """
    print(f"--- Calling Stability AI API to generate image for prompt: '{prompt}' ---")
    api_url = "https://api.stability.ai/v2beta/stable-image/generate/sd3"
    api_key = os.getenv("STABILITY_API_KEY")
    if not api_key: return "Error: STABILITY_API_KEY environment variable not set."
    
    headers = {"authorization": f"Bearer {api_key}", "accept": "image/*"}
    
    # Using the more reliable 'sd3' model
    files = {'prompt': (None, prompt), 'model': (None, 'sd3'), 'output_format': (None, 'png')}
    
    try:
        response = requests.post(api_url, headers=headers, files=files, timeout=45)
        response.raise_for_status() # Check for HTTP errors
        
        # 1. Create the directory if it doesn't exist
        if not os.path.exists("generated_images"):
            os.makedirs("generated_images")

        # 2. Generate a unique filename
        image_filename = f"{uuid.uuid4()}.png"
        image_filepath = os.path.join("generated_images", image_filename)

        # 3. Save the image content to the file
        with open(image_filepath, "wb") as f:
            f.write(response.content)
        
        print(f"--- Image generation success. Saved to {image_filepath} ---")

        # 4. Return a URL that the FastAPI server will provide
        image_url = f"http://127.0.0.1:8000/images/{image_filename}"
        return f"IMAGE_URL::{image_url}"

    except requests.exceptions.HTTPError as http_err:
        error_details = http_err.response.text
        print(f"--- Stability AI HTTP Error: {http_err.response.status_code} - {error_details} ---")
        return f"Stability AI API Error: {http_err.response.status_code} - {error_details}"
    except Exception as e:
        print(f"--- Stability AI Request Error: {e} ---")
        return f"Stability AI request error: {e}"


all_tools = [
    reasoning_tool,
    coding_tool,
    mistral_tool,
    search_for_image_tool,
    generate_image_tool,
]
