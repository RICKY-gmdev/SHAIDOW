import os
import uuid
from typing import Any, List
import httpx
from langchain_core.tools import tool
from langchain_core.messages import BaseMessage
from langchain_mistralai import ChatMistralAI
from langchain_groq import ChatGroq
from pydantic import SecretStr

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

def _mistral() -> ChatMistralAI:
    mistral_key = os.getenv("MISTRAL_API_KEY")
    return ChatMistralAI(
        model_name="mistral-large-latest",
        temperature=0,
        api_key=SecretStr(mistral_key) if mistral_key else None,
    )

def _extract_content(resp: Any) -> str:
    if resp is None: 
        return "No content."
    if isinstance(resp, str): 
        return resp.strip() or "No content."
    if isinstance(resp, BaseMessage):
        c = resp.content
        if isinstance(c, list):
            parts = [str(p.get("text")) for p in c if isinstance(p, dict) and p.get("text")]
            c = "\n".join(parts)
        return str(c).strip() or "No content."
    return str(resp)[:4000] or "No content."

async def _groq_chat_async(model: str, query: str, system_prompt: str) -> str:
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
        "max_tokens": 2048,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(GROQ_URL, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            return f"Groq error: {e}"

@tool
async def reasoning_tool(query: str) -> str:
    """General reasoning and versatile Q&A."""
    return await _groq_chat_async(
        "qwen/qwen3-32b", 
        query, 
        "You are a helpful assistant with strong reasoning abilities."
    )

@tool
async def coding_tool(query: str) -> str:
    """Use for coding, debugging, and clean code generation."""
    return await _groq_chat_async(
        "llama-3.1-8b-instant", 
        query, 
        "You are an expert coding assistant. Generate clean, working code."
    )

@tool
async def mistral_tool(query: str) -> str:
    """Quick, factual answers, summaries, and general knowledge lookup."""
    try:
        response = await _mistral().ainvoke(query)
        return _extract_content(response)
    except Exception as e:
        return f"Error invoking Mistral tool: {e}"

@tool
async def search_for_image_tool(query: str) -> str:
    """Search for a real image using the Pexels API and return a URL."""
    api_key = os.getenv("PEXELS_API_KEY")
    if not api_key:
        return "Error: PEXELS_API_KEY environment variable not set."

    headers = {"Authorization": api_key}
    url = f"https://api.pexels.com/v1/search?query={query}&per_page=1"

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            if data.get("photos"):
                return f"IMAGE_URL::{data['photos'][0]['src']['large']}"
            return "No images found."
        except Exception as e:
            return f"Pexels search error: {e}"

@tool
async def generate_image_tool(prompt: str) -> str:
    """Create or generate a completely new image from a text description."""
    api_url = "https://api.stability.ai/v2beta/stable-image/generate/sd3"
    api_key = os.getenv("STABILITY_API_KEY")
    if not api_key:
        return "Error: STABILITY_API_KEY environment variable not set."

    headers = {"authorization": f"Bearer {api_key}", "accept": "image/*"}
    files = {
        'prompt': (None, prompt),
        'model': (None, 'sd3.5-flash'),
        'output_format': (None, 'png')
    }

    async with httpx.AsyncClient(timeout=45.0) as client:
        try:
            # httpx format for multipart file/form uploads
            resp = await client.post(api_url, headers=headers, files=files)
            resp.raise_for_status()

            os.makedirs("generated_images", exist_ok=True)
            image_filename = f"{uuid.uuid4()}.png"
            image_filepath = os.path.join("generated_images", image_filename)

            with open(image_filepath, "wb") as f:
                f.write(resp.content)

            return f"IMAGE_URL::/images/{image_filename}"
        except Exception as e:
            return f"Stability AI error: {e}"

all_tools = [reasoning_tool, coding_tool, mistral_tool, search_for_image_tool, generate_image_tool]