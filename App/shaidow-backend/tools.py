import os
import re
import uuid
import base64
from typing import Any
from urllib.parse import quote
import httpx
from langchain_core.tools import tool
from langchain_core.messages import BaseMessage
from langchain_mistralai import ChatMistralAI
from pydantic import SecretStr

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SHAIDOW_VOICE = (
    "You are SHAIDOW, a loyal, sharp, pragmatic, and slightly futuristic AI ally "
    "created by Ricky (Md Ayman Iqbal). Structure your response clearly using markdown headings, "
    "bullet points, and fenced code blocks with language tags (e.g., ```csharp or ```python). "
    "End with 1-2 concise, proactive next steps."
)


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
        f"{SHAIDOW_VOICE}\nYou are operating as SHAIDOW's Deep Reasoning Specialist. Provide a thorough, logically structured analysis and solution.",
        temperature=0.3,
    )


@tool
async def coding_tool(query: str) -> str:
    """Delegate ALL programming, software engineering, code generation, debugging, SQL, C#, .NET, Python, or algorithm tasks."""
    return await _groq_chat_async(
        ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "llama-3.1-8b-instant"],
        query,
        f"{SHAIDOW_VOICE}\nYou are operating as SHAIDOW's Principal Software Engineer. Write production-ready, well-structured code inside fenced markdown code blocks with clear step-by-step explanations and time/space complexity where relevant.",
        temperature=0.1,
    )


@tool
async def mistral_tool(query: str) -> str:
    """Delegate factual lookups, general knowledge, historical/geographical summaries, itineraries, definitions, and quick explanations."""
    try:
        prompt = f"{SHAIDOW_VOICE}\n\nUser request: {query}"
        response = await _mistral().ainvoke(prompt)
        return _extract_content(response)
    except Exception as e:
        return f"Error invoking Mistral specialist: {e}"


@tool
async def web_search_tool(query: str) -> str:
    """Search the live web for current events, recent news, live facts, sports schedules, or up-to-date documentation."""
    tavily_key = os.getenv("TAVILY_API_KEY")
    snippets: list[str] = []

    async with httpx.AsyncClient(timeout=20.0) as client:
        # 1. Use Tavily Search API if TAVILY_API_KEY is configured in Azure
        if tavily_key:
            try:
                resp = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": tavily_key,
                        "query": query,
                        "search_depth": "basic",
                        "include_answer": True,
                        "max_results": 5,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("answer"):
                        snippets.append(f"**Direct Answer:** {data['answer']}")
                    for item in data.get("results", []):
                        snippets.append(
                            f"- **{item.get('title')}** ({item.get('url')}): {item.get('content')}"
                        )
                    if snippets:
                        return "\n".join(snippets)
            except Exception:
                pass

        # 2. Zero-Key Fallback: DuckDuckGo Instant Answer + Wikipedia Search API
        try:
            ddg_resp = await client.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            )
            if ddg_resp.status_code == 200:
                ddg_data = ddg_resp.json()
                if ddg_data.get("AbstractText"):
                    snippets.append(
                        f"**Summary ({ddg_data.get('AbstractSource', 'Web')}):** {ddg_data['AbstractText']} ({ddg_data.get('AbstractURL', '')})"
                    )
                for topic in ddg_data.get("RelatedTopics", [])[:4]:
                    if isinstance(topic, dict) and topic.get("Text"):
                        snippets.append(f"- {topic['Text']}")
        except Exception:
            pass

        try:
            wiki_resp = await client.get(
                "https://en.wikipedia.org/w/api.php",
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": query,
                    "format": "json",
                    "srlimit": 3,
                },
                headers={"User-Agent": "SHAIDOW-Agent/4.1 (https://github.com/RICKY-gmdev/SHAIDOW)"},
            )
            if wiki_resp.status_code == 200:
                search_items = wiki_resp.json().get("query", {}).get("search", [])
                for item in search_items:
                    clean_snippet = re.sub(r"<[^>]+>", "", item.get("snippet", ""))
                    snippets.append(f"- **Wikipedia ({item.get('title')}):** {clean_snippet}")
        except Exception:
            pass

    if snippets:
        return "\n".join(snippets)
    return f"No live web results found for '{query}'. Please answer using best available knowledge."


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

    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        # 1. Try Stability AI first if key is present and has credits
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
                    b64_img = base64.b64encode(resp.content).decode("utf-8")
                    return f"IMAGE_URL::data:image/png;base64,{b64_img}"
            except Exception:
                pass  # Fall through to permanent cloud Flux URL

        # 2. Permanent Cloud URL Fallback (Pollinations Flux — never 404s on Azure container restart)
        try:
            encoded_prompt = quote(prompt)
            seed = uuid.uuid4().int % 1000000
            free_url = (
                f"https://image.pollinations.ai/prompt/{encoded_prompt}"
                f"?width=1024&height=1024&seed={seed}&nologo=true&model=flux"
            )
            return f"IMAGE_URL::{free_url}"
        except Exception as e:
            return f"Image generation error: {e}"


all_tools = [
    reasoning_tool,
    coding_tool,
    mistral_tool,
    web_search_tool,
    search_for_image_tool,
    generate_image_tool,
]
