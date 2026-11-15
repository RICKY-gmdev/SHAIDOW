import os
import re
import uuid
from typing import Any
from urllib.parse import quote
import httpx
from langchain_core.tools import tool
from langchain_core.messages import BaseMessage
from langchain_mistralai import ChatMistralAI
from pydantic import SecretStr

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def _mistral() -> ChatMistralAI:
    mistral_key = os.getenv("MISTRAL_API_KEY")
    return ChatMistralAI(
        model_name="mistral-large-latest",
        temperature=0.1,
        api_key=SecretStr(mistral_key) if mistral_key else None,
    )


def _clean_llm_text(text: str) -> str:
    """Strips <think>...</think> blocks from reasoning models."""
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    return cleaned.strip() or "No content."


def _extract_content(resp: Any) -> str:
    if resp is None:
        return "No content."
    if isinstance(resp, str):
        return _clean_llm_text(resp)
    if isinstance(resp, BaseMessage):
        c = resp.content
        if isinstance(c, list):
            parts = [str(p.get("text")) for p in c if isinstance(p, dict) and p.get("text")]
            c = "\n".join(parts)
        return _clean_llm_text(str(c))
    return _clean_llm_text(str(resp)[:4000])


async def _groq_chat_async(
    models: list[str], query: str, system_prompt: str, temperature: float = 0.2
) -> str:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return "Error: GROQ_API_KEY not set."

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    last_error = ""

    async with httpx.AsyncClient(timeout=45.0) as client:
        for model in models:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query},
                ],
                "temperature": temperature,
                "max_tokens": 3072,
            }
            try:
                resp = await client.post(GROQ_URL, json=payload, headers=headers)
                if resp.status_code in (400, 404):
                    last_error = f"{model} returned {resp.status_code}: {resp.text}"
                    continue
                resp.raise_for_status()
                data = resp.json()
                raw_content = data["choices"][0]["message"]["content"]
                return _clean_llm_text(raw_content)
            except Exception as e:
                last_error = str(e)
                continue

    # Final fallback to Mistral if all Groq model IDs fail
    try:
        fallback_resp = await _mistral().ainvoke(f"{system_prompt}\n\nUser request: {query}")
        return _extract_content(fallback_resp)
    except Exception as e:
        return f"Specialist error: {last_error} | Fallback error: {e}"


@tool
async def reasoning_tool(query: str) -> str:
    """Delegate complex reasoning, system architecture, math, analysis, creative planning, or multi-step problem solving."""
    return await _groq_chat_async(
        ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "llama-3.1-8b-instant"],
        query,
        "You are a deep reasoning specialist. Provide a thorough, logically structured analysis and solution.",
        temperature=0.3,
    )


@tool
async def coding_tool(query: str) -> str:
    """Delegate ALL programming, software engineering, code generation, debugging, SQL, C#, .NET, Python, or algorithm tasks."""
    return await _groq_chat_async(
        ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "llama-3.1-8b-instant"],
        query,
        "You are a principal software engineer. Write production-ready, well-structured code inside fenced markdown code blocks (e.g., ```python or ```csharp) with clear step-by-step explanations.",
        temperature=0.1,
    )


@tool
async def mistral_tool(query: str) -> str:
    """Delegate factual lookups, general knowledge, historical/geographical summaries, definitions, and quick explanations."""
    try:
        response = await _mistral().ainvoke(query)
        return _extract_content(response)
    except Exception as e:
        return f"Error invoking Mistral specialist: {e}"


@tool
async def search_for_image_tool(query: str) -> str:
    """Search for a real-world photograph using Pexels and return its IMAGE_URL."""
    api_key = os.getenv("PEXELS_API_KEY")
    if not api_key:
        return "Error: PEXELS_API_KEY environment variable not set."

    headers = {"Authorization": api_key}
    url = "https://api.pexels.com/v1/search"

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(url, params={"query": query, "per_page": 1}, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            if data.get("photos"):
                return f"IMAGE_URL::{data['photos'][0]['src']['large']}"
            return "No matching real-world images found."
        except Exception as e:
            return f"Pexels search error: {e}"


@tool
async def generate_image_tool(prompt: str) -> str:
    """Generate a brand-new AI artwork or illustration from a detailed text prompt."""
    api_url = "https://api.stability.ai/v2beta/stable-image/generate/sd3"
    api_key = os.getenv("STABILITY_API_KEY")

    os.makedirs("generated_images", exist_ok=True)
    image_filename = f"{uuid.uuid4()}.png"
    image_filepath = os.path.join("generated_images", image_filename)

    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        # 1. Try Stability AI first if key is present
        if api_key:
            headers = {"authorization": f"Bearer {api_key}", "accept": "image/*"}
            files = {
                "prompt": (None, prompt),
                "model": (None, "sd3.5-flash"),
                "output_format": (None, "png"),
            }
            try:
                resp = await client.post(api_url, headers=headers, files=files)
                if resp.status_code == 200:
                    with open(image_filepath, "wb") as f:
                        f.write(resp.content)
                    return f"IMAGE_URL::/images/{image_filename}"
            except Exception:
                pass  # Fall through to free Flux generator

        # 2. Automatic Free Fallback (Flux via Pollinations — no API key or credits needed)
        try:
            encoded_prompt = quote(prompt)
            seed = uuid.uuid4().int % 1000000
            free_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&seed={seed}&nologo=true&model=flux"
            resp = await client.get(free_url)
            resp.raise_for_status()

            with open(image_filepath, "wb") as f:
                f.write(resp.content)

            return f"IMAGE_URL::/images/{image_filename}"
        except Exception as e:
            return f"Image generation error: {e}"


all_tools = [
    reasoning_tool,
    coding_tool,
    mistral_tool,
    search_for_image_tool,
    generate_image_tool,
]
