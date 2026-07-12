import os
import asyncio
import requests
from typing import Any, List
from langchain_core.tools import tool
from langchain_core.messages import BaseMessage
from langchain_mistralai import ChatMistralAI
from pydantic import SecretStr
import uuid

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def _mistral():
    mistral_key = os.getenv("MISTRAL_API_KEY")
    return ChatMistralAI(
        model_name="mistral-large-latest",
        temperature=0,
        api_key=SecretStr(mistral_key) if mistral_key else None,
    )


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


def _groq_chat_sync(model: str, query: str, system_prompt: str = "You are a helpful assistant.") -> str:
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

    try:
        resp = requests.post(GROQ_URL, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"Groq error: {e}"


def _mistral_invoke_sync(query: str) -> str:
    print("--- INVOKING MISTRAL TOOL ---")
    try:
        response = _mistral().invoke(query)
        return _extract_content(response)
    except Exception as e:
        return f"Error invoking Mistral tool: {e}"


def _pexels_search_sync(query: str) -> str:
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


def _stability_generate_sync(prompt: str) -> str:
    print(f"--- Calling Stability AI API to generate image for prompt: '{prompt}' ---")
    api_url = "https://api.stability.ai/v2beta/stable-image/generate/sd3"
    api_key = os.getenv("STABILITY_API_KEY")
    if not api_key:
        return "Error: STABILITY_API_KEY environment variable not set."

    headers = {"authorization": f"Bearer {api_key}", "accept": "image/*"}
    files = {'prompt': (None, prompt), 'model': (None, 'sd3.5-flash'), 'output_format': (None, 'png')}

    try:
        response = requests.post(api_url, headers=headers, files=files, timeout=45)
        response.raise_for_status()

        if not os.path.exists("generated_images"):
            os.makedirs("generated_images")

        image_filename = f"{uuid.uuid4()}.png"
        image_filepath = os.path.join("generated_images", image_filename)

        with open(image_filepath, "wb") as f:
            f.write(response.content)

        print(f"--- Image generation success. Saved to {image_filepath} ---")
        image_url = f"/images/{image_filename}"
        return f"IMAGE_URL::{image_url}"

    except requests.exceptions.HTTPError as http_err:
        error_details = http_err.response.text
        print(f"--- Stability AI HTTP Error: {http_err.response.status_code} - {error_details} ---")
        return f"Stability AI API Error: {http_err.response.status_code} - {error_details}"
    except Exception as e:
        print(f"--- Stability AI Request Error: {e} ---")
        return f"Stability AI request error: {e}"


# Every tool below is defined as `async def` and offloads its actual blocking
# network call to a background thread via asyncio.to_thread. This matters:
# `requests` is synchronous, OS-blocking I/O. If these ran as plain sync
# functions, each call would freeze Python's single asyncio event loop -
# which is also responsible for flushing bytes to the SSE connection. That's
# exactly what was causing the "frozen, then dumps everything at once"
# behavior: the loop couldn't write any queued stream data while a tool's
# network call was in progress.

@tool
async def reasoning_tool(query: str) -> str:
    """General reasoning and versatile Q&A."""
    return await asyncio.to_thread(
        _groq_chat_sync,
        "qwen/qwen3-32b",
        query,
        "You are a helpful assistant with strong reasoning abilities.",
    )


@tool
async def coding_tool(query: str) -> str:
    """Use for coding, debugging, and clean code generation."""
    return await asyncio.to_thread(
        _groq_chat_sync,
        "llama-3.1-8b-instant",
        query,
        "You are an expert coding assistant. Generate clean, working code.",
    )


@tool
async def mistral_tool(query: str) -> str:
    """Quick, factual answers, summaries, and general knowledge lookup."""
    return await asyncio.to_thread(_mistral_invoke_sync, query)


@tool
async def search_for_image_tool(query: str) -> str:
    """Search for a real image using the Pexels API and return a URL."""
    return await asyncio.to_thread(_pexels_search_sync, query)


@tool
async def generate_image_tool(prompt: str) -> str:
    """
    Use this tool to create or generate a completely new image from a text description.
    Saves the image to a file and returns a URL to it.
    """
    return await asyncio.to_thread(_stability_generate_sync, prompt)


all_tools = [
    reasoning_tool,
    coding_tool,
    mistral_tool,
    search_for_image_tool,
    generate_image_tool,
]
