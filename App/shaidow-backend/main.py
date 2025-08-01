# main.py

import os
import uuid
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agent import create_agent_graph, AgentState
from langgraph.checkpoint.memory import MemorySaver


load_dotenv()


SYSTEM_PROMPT = ""

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan event handler. This runs once on startup.
    It loads the system prompt from a file.
    """
    global SYSTEM_PROMPT
    try:
        with open("system_prompt.txt", "r", encoding="utf-8") as f:
            SYSTEM_PROMPT = f.read()
        print("System prompt loaded successfully.")
    except FileNotFoundError:
        print("WARNING: system_prompt.txt not found. Agent will use a default prompt.")
        SYSTEM_PROMPT = "You are a helpful AI assistant named SHAIDOW."
    
    
    yield
  
    print("Application shutting down.")


app = FastAPI(
    title="SHAIDOW Agentic Core API",
    version="4.0.0",
    lifespan=lifespan
)
@app.get("/")
def read_root():
    return {"message": "Welcome to the Shaidow API"}

agent_executor = create_agent_graph()

memory = MemorySaver()

class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = Field(
        default=None,
        description="A unique identifier for the conversation thread. If not provided, a new one will be created."
    )


@app.post("/chat")
async def chat(req: ChatRequest):
    """
    Main chat endpoint. Receives a message and an optional thread_id,
    streams the agent's response back.
    """
    thread_id = req.thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    
    initial_state: AgentState = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": req.message}
        ]
    }

    async def event_stream():
        """
        Generator function to stream agent responses.
        We use astream_events to get detailed events from the graph.
        """
        try:
           
            async for event in agent_executor.astream_events(initial_state, config, version="v1"):
                kind = event["event"]
                
                if kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if chunk.content:
                        
                        yield f"data: {{\"type\": \"text_chunk\", \"content\": \"{chunk.content}\"}}\n\n"
                
                elif kind == "on_tool_start":
                    tool_name = event["name"]
                    yield f"data: {{\"type\": \"tool_start\", \"tool\": \"{tool_name}\"}}\n\n"
                
                elif kind == "on_tool_end":
                    tool_output = event["data"].get("output")
                    if tool_output:
                        
                        clean_output = str(tool_output).replace("\n", "\\n").replace("\"", "\\\"")
                        yield f"data: {{\"type\": \"tool_end\", \"output\": \"{clean_output}\"}}\n\n"
            
            
            yield f"data: {{\"type\": \"stream_end\", \"thread_id\": \"{thread_id}\"}}\n\n"

        except Exception as e:
            print(f"Error during stream: {e}")
            yield f"data: {{\"type\": \"error\", \"content\": \"An error occurred: {str(e)}\"}}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")