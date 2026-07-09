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

if not os.path.exists("generated_images"):
    os.makedirs("generated_images")

SYSTEM_PROMPT = ""
memory = MemorySaver()
agent_executor = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global SYSTEM_PROMPT
    global agent_executor

    try:
        with open("system_prompt.txt", "r", encoding="utf-8") as f:
            SYSTEM_PROMPT = f.read()
            print("System prompt loaded successfully.")
    except FileNotFoundError:
        print("WARNING: system_prompt.txt not found.")
        
    try:
        initialize_agent()
        print("Agent model initialized successfully.")
        agent_executor = create_agent_graph(SYSTEM_PROMPT).with_config(checkpointer=memory)
        print("Agent executor created successfully.")
    except ValueError as e:
        print(f"ERROR: Failed to initialize agent - {e}")
        print("The server will start but chat functionality will not work without GOOGLE_API_KEY.")
        agent_executor = None
    
    yield
    
    print("Application shutting down.")

app = FastAPI(title="SHAIDOW Agentic Core API", version="4.0.2", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/images", StaticFiles(directory="generated_images"), name="images")

@app.get("/")
def read_root():
    return {"message": "Welcome to the SHAIDOW API", "version": "4.0.2"}

class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = Field(default=None)

@app.get("/images", response_model=List[str])
async def get_images(request: Request):
    """Scans the generated_images directory and returns a list of full URLs."""
    image_urls = []
    image_dir = "generated_images"
    if os.path.exists(image_dir):
        files = sorted(
            [os.path.join(image_dir, f) for f in os.listdir(image_dir) if f.endswith(".png")],
            key=os.path.getmtime,
            reverse=True
        )
        base_url = str(request.base_url).rstrip('/')
        for filepath in files:
            filename = os.path.basename(filepath)
            image_urls.append(f"{base_url}/images/{filename}")
    return image_urls

@app.post("/chat")
async def chat(req: ChatRequest):
    if agent_executor is None:
        return {"error": "Agent not initialized"}

    executor = agent_executor  # type assertion for type checker
    thread_id = req.thread_id or str(uuid.uuid4())
    config: RunnableConfig = {"configurable": {"thread_id": thread_id}}

    user_input = {"messages": [("user", req.message)]}

    async def event_stream():
        print("\n--- NEW REQUEST RECEIVED ---")
        try:
            async for event in executor.astream_events(user_input, config, version="v2"):
                kind = event.get("event")
                
                if kind == "on_chat_model_stream":
                    # Only forward chunks from the router node - direct answers
                    # stream token-by-token from here.
                    node = event.get("metadata", {}).get("langgraph_node")
                    if node != "router":
                        continue
                    event_data = event.get("data", {})
                    chunk = event_data.get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        data = json.dumps({"type": "text_chunk", "content": chunk.content})
                        yield f"data: {data}\n\n"

                elif kind == "on_chain_end" and event.get("name") == "finalize":
                    output = event.get("data", {}).get("output", {})
                    finalized_messages = output.get("messages", []) if isinstance(output, dict) else []
                    if finalized_messages:
                        content = finalized_messages[-1].content
                        if content:
                            data = json.dumps({"type": "text_chunk", "content": content})
                            yield f"data: {data}\n\n"
                
                elif kind == "on_tool_start":
                    tool_name = event.get("name")
                    data = json.dumps({"type": "tool_start", "tool": tool_name})
                    yield f"data: {data}\n\n"
                
                elif kind == "on_tool_end":
                    event_data = event.get("data", {})
                    tool_output = event_data.get("output")
                    clean_output = str(tool_output) if tool_output else ""
                    tool_name = event.get("name")
                    data = json.dumps({"type": "tool_end", "tool": tool_name, "output": clean_output.strip()})
                    yield f"data: {data}\n\n"
            
            data = json.dumps({"type": "stream_end", "thread_id": thread_id})
            yield f"data: {data}\n\n"

        except Exception as e:
            print(f"!!!!!!!! STREAMER ERROR!!!!!!!!\n{e}\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            error_message = str(e).replace('"', "'")
            data = json.dumps({"type": "error", "content": f"An error occurred: {error_message}"})
            yield f"data: {data}\n\n"
        
        print("--- REQUEST COMPLETED ---\n")

    return StreamingResponse(event_stream(), media_type="text/event-stream")
