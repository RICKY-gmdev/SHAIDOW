#main.py
import os
import uuid
import json
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from fastapi.staticfiles import StaticFiles
from typing import List
from langchain_core.runnables import RunnableConfig

from agent import create_agent_graph, initialize_agent
from langgraph.checkpoint.memory import MemorySaver

load_dotenv()
os.makedirs("generated_images", exist_ok=True)

SYSTEM_PROMPT = ""
memory = MemorySaver()
agent_executor = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global SYSTEM_PROMPT, agent_executor
    
    try:
        with open("system_prompt.txt", "r", encoding="utf-8") as f:
            SYSTEM_PROMPT = f.read()
    except FileNotFoundError:
        print("WARNING: system_prompt.txt not found. Defaulting to empty.")
        
    try:
        initialize_agent()
        agent_executor = create_agent_graph(SYSTEM_PROMPT).with_config(checkpointer=memory)
        print("Agent Engine Status: Online.")
    except ValueError as e:
        print(f"ERROR: Failed to initialize agent - {e}")
        agent_executor = None
    yield

app = FastAPI(title="SHAIDOW Agentic Core API", version="4.0.2", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/images", StaticFiles(directory="generated_images"), name="images")

class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = Field(default=None)

@app.get("/")
def read_root():
    return {"status": "healthy", "version": "4.0.2"}

@app.post("/chat")
async def chat(req: ChatRequest):
    if agent_executor is None:
        return {"error": "Agent not initialized or missing configuration API keys."}

    thread_id = req.thread_id or str(uuid.uuid4())
    config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
    user_input = {"messages": [("user", req.message)]}

    async def event_stream():
        try:
            # localize and assert executor to satisfy static/ runtime checks
            executor = agent_executor
            if executor is None:
                yield f"data: {json.dumps({'type': 'error', 'content': 'Agent executor unavailable'})}\n\n"
                return
            # type: ignore - executor may be dynamically typed, ensure attribute exists at runtime
            async for event in executor.astream_events(user_input, config, version="v2"):
                kind = event.get("event")
                
                # Stream normal text responses token-by-token
                if kind == "on_chat_model_stream":
                    node = event.get("metadata", {}).get("langgraph_node")
                    if node != "router":
                        continue
                    
                    chunk = event.get("data", {}).get("chunk")
                    # CRITICAL FIX: Ensure we aren't streaming tool_call raw text chunks to the user
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        if not getattr(chunk, "tool_calls", None):
                            data = json.dumps({"type": "text_chunk", "content": chunk.content})
                            yield f"data: {data}\n\n"

                # Stream status notifications for tools
                elif kind == "on_tool_start":
                    data = json.dumps({"type": "tool_start", "tool": event.get("name")})
                    yield f"data: {data}\n\n"
                
                elif kind == "on_tool_end":
                    tool_output = event.get("data", {}).get("output")
                    if tool_output is None:
                        clean_output = ""
                    elif hasattr(tool_output, "content") and getattr(tool_output, "content") is not None:
                        clean_output = str(tool_output.content)
                    else:
                        clean_output = str(tool_output)

                    data = json.dumps({
                        "type": "tool_end",
                        "tool": event.get("name"),
                        "output": clean_output.strip()
                    })
                    yield f"data: {data}\n\n"
            
            # Finalize Stream cleanly
            yield f"data: {json.dumps({'type': 'stream_end', 'thread_id': thread_id})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': f'Stream crashed: {str(e)}'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")