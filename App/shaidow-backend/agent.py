import os
from typing import List, Dict, Any, Optional
from functools import partial
from langchain_core.messages import (
    HumanMessage,
    ToolMessage,
    SystemMessage,
    BaseMessage,
    AIMessage,
)
from langgraph.graph import StateGraph, END, MessagesState
from langgraph.prebuilt import ToolNode
from langchain_google_genai import ChatGoogleGenerativeAI
from tools import all_tools

agent_model: Optional[ChatGoogleGenerativeAI] = None
agent_with_tools = None
tool_node = ToolNode(all_tools)

def initialize_agent():
    """Initialize the agent model with Google API key validation."""
    global agent_model, agent_with_tools
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY environment variable is required. "
            "Please set it in Replit Secrets or your .env file. "
            "Get your key at: https://aistudio.google.com/apikey"
        )
    
    agent_model = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        convert_system_message_to_human=True,
        temperature=0.2,
        google_api_key=api_key,
    )
    
    agent_with_tools = agent_model.bind_tools(all_tools)
    return agent_model

def _ensure_system_first(messages: List[BaseMessage], system_prompt: str) -> List[BaseMessage]:
    if not messages or not isinstance(messages[0], SystemMessage):
        return [SystemMessage(content=system_prompt.strip())] + messages
    return messages

def call_model(state: MessagesState, config: dict) -> Dict[str, Any]:
    if agent_with_tools is None:
        raise RuntimeError("Agent not initialized. Call initialize_agent() first.")
    system_prompt = config["configurable"].get("system_prompt", "You are a helpful assistant.")
    messages = state["messages"]
    messages_with_system_prompt = _ensure_system_first(messages, system_prompt)
    response = agent_with_tools.invoke(messages_with_system_prompt)
    return {"messages": [response]}

def should_continue(state: MessagesState) -> str:
    last_message = state['messages'][-1]
    if hasattr(last_message, "tool_calls") and len(last_message.tool_calls) > 0:
        return "tools"
    return END

def sanitize_tool_output(state: MessagesState) -> Dict[str, Any]:
    last_message = state['messages'][-1]
    if isinstance(last_message, ToolMessage):
        if isinstance(last_message.content, str) and last_message.content.startswith("IMAGE_DATA::"):
            last_message.content = "[Image was generated successfully and displayed to the user.]"
    return {"messages": [last_message]}

def create_agent_graph(system_prompt: str):
    workflow = StateGraph(MessagesState)
    agent_node = partial(call_model, config={"configurable": {"system_prompt": system_prompt}})
    
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)
    workflow.add_node("sanitize_tools", sanitize_tool_output)

    workflow.set_entry_point("agent")
    
    workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    workflow.add_edge("tools", "sanitize_tools")
    workflow.add_edge("sanitize_tools", "agent")

    return workflow.compile()
