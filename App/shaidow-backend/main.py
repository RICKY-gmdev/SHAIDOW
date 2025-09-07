import os
import uuid
import json
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agent import create_agent_graph
from langgraph.checkpoint.memory import MemorySaver

load_dotenv()

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
        SYSTEM_PROMPT = "You are a helpful AI assistant."
    
    agent_executor = create_agent_graph(SYSTEM_PROMPT).with_config(checkpointer=memory)
    print("Agent executor created successfully.")
    
    yield
    
    print("Application shutting down.")

app = FastAPI(title="SHAIDOW Agentic Core API", version="4.0.2", lifespan=lifespan)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Shaidow API"}

class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = Field(default=None)

@app.post("/chat")
async def chat(req: ChatRequest):
    if agent_executor is None:
        return {"error": "Agent not initialized"}

    thread_id = req.thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    user_input = {"messages": [("user", req.message)]}

    async def event_stream():
        print("\n--- NEW REQUEST RECEIVED ---")
        try:
            async for event in agent_executor.astream_events(user_input, config, version="v1"):
                kind = event["event"]
                
                if kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if chunk.content:
                        data = json.dumps({"type": "text_chunk", "content": chunk.content})
                        yield f"data: {data}\n\n"
                
                elif kind == "on_tool_start":
                    tool_name = event["name"]
                    data = json.dumps({"type": "tool_start", "tool": tool_name})
                    yield f"data: {data}\n\n"
                
                elif kind == "on_tool_end":
                    tool_output = event["data"].get("output")
                    clean_output = str(tool_output) if tool_output else ""
                    data = json.dumps({"type": "tool_end", "tool": event["name"], "output": clean_output.strip()})
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