import os
import uuid
import json
import traceback
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from fastapi.staticfiles import StaticFiles
from langchain_core.runnables import RunnableConfig

from agent import create_agent_graph, initialize_agent
from langgraph.checkpoint.memory import MemorySaver

load_dotenv()
os.makedirs("generated_images", exist_ok=True)

SYSTEM_PROMPT = ""
memory = MemorySaver()
agent_executor = None
STARTUP_ERROR = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global SYSTEM_PROMPT, agent_executor, STARTUP_ERROR

    try:
        with open("system_prompt.txt", "r", encoding="utf-8") as f:
            SYSTEM_PROMPT = f.read()
    except FileNotFoundError:
        print("WARNING: system_prompt.txt not found. Defaulting to empty.")

    try:
        initialize_agent()
        agent_executor = create_agent_graph(SYSTEM_PROMPT, checkpointer=memory)
        STARTUP_ERROR = None
        print("Agent Engine Status: Online.")
    except Exception as e:
        STARTUP_ERROR = f"{type(e).__name__}: {str(e)}"
        print(f"ERROR: Failed to initialize agent - {STARTUP_ERROR}")
        traceback.print_exc()
        agent_executor = None
    yield


app = FastAPI(title="SHAIDOW Agentic Core API", version="4.0.3", lifespan=lifespan)

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
    return {
        "status": "healthy",
        "version": "4.0.3",
        "agent_ready": agent_executor is not None,
        "startup_error": STARTUP_ERROR,
    }


@app.post("/chat")
async def chat(req: ChatRequest):
    thread_id = req.thread_id or str(uuid.uuid4())
    config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
    user_input = {"messages": [("user", req.message)]}

    async def event_stream():
        try:
            if agent_executor is None:
                err_msg = STARTUP_ERROR or "Agent not initialized or missing API keys."
                yield f"data: {json.dumps({'type': 'error', 'content': f'ML Startup Error: {err_msg}'})}\n\n"
                yield f"data: {json.dumps({'type': 'stream_end', 'thread_id': thread_id})}\n\n"
                return

            streamed_any_text = False

            async for event in agent_executor.astream_events(user_input, config, version="v2"):
                kind = event.get("event")

                if kind == "on_chat_model_stream":
                    node = event.get("metadata", {}).get("langgraph_node")
                    if node not in ("router", "finalize"):
                        continue

                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        has_tool_calls = bool(
                            getattr(chunk, "tool_calls", None)
                            or getattr(chunk, "tool_call_chunks", None)
                        )
                        if not has_tool_calls and isinstance(chunk.content, str):
                            streamed_any_text = True
                            data = json.dumps({"type": "text_chunk", "content": chunk.content})
                            yield f"data: {data}\n\n"

                elif kind == "on_chain_end" and event.get("name") == "finalize" and not streamed_any_text:
                    output_data = event.get("data", {}).get("output")
                    if isinstance(output_data, dict):
                        output_messages = output_data.get("messages", [])
                        if output_messages:
                            last_msg = output_messages[-1]
                            content = getattr(last_msg, "content", "")
                            if content:
                                streamed_any_text = True
                                data = json.dumps({"type": "text_chunk", "content": str(content)})
                                yield f"data: {data}\n\n"

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
                        "output": clean_output.strip(),
                    })
                    yield f"data: {data}\n\n"

            yield f"data: {json.dumps({'type': 'stream_end', 'thread_id': thread_id})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': f'Stream crashed: {str(e)}'})}\n\n"
            yield f"data: {json.dumps({'type': 'stream_end', 'thread_id': thread_id})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
