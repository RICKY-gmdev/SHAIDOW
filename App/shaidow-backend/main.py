import os
import uuid
import json
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
        agent_executor = create_agent_graph(SYSTEM_PROMPT, checkpointer=memory)
        print("Agent Engine Status: Online.")
    except Exception as e:
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
            executor = agent_executor
            if executor is None:
                yield f"data: {json.dumps({'type': 'error', 'content': 'Agent executor unavailable'})}\n\n"
                return

            streamed_any_text = False

            async for event in executor.astream_events(user_input, config, version="v2"):
                kind = event.get("event")

                # Stream tokens from BOTH direct router replies AND synthesized finalize replies
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

                # Catch static or fallback AIMessages from finalize if LLM streaming didn't run
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

                # Stream status notifications when a specialist tool starts
                elif kind == "on_tool_start":
                    data = json.dumps({"type": "tool_start", "tool": event.get("name")})
                    yield f"data: {data}\n\n"

                # Stream tool completion (used by frontend to render IMAGE_URL:: bubbles, etc.)
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

            # Finalize Stream cleanly
            yield f"data: {json.dumps({'type': 'stream_end', 'thread_id': thread_id})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': f'Stream crashed: {str(e)}'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
