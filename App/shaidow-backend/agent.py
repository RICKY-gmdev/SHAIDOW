# agent.py
from typing import List, Dict, Any
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


agent_model = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    convert_system_message_to_human=True,
    temperature=0.2,
)

agent_with_tools = agent_model.bind_tools(all_tools)
tool_node = ToolNode(all_tools)


def _ensure_system_first(messages: List[BaseMessage], system_prompt: str) -> List[BaseMessage]:
    if not messages:
        return [SystemMessage(content=system_prompt.strip())]
    first = messages[0]
    if not isinstance(first, SystemMessage):
        return [SystemMessage(content=system_prompt.strip())] + list(messages)
    return list(messages)



def call_model(state: MessagesState) -> Dict[str, Any]:
    messages: List[BaseMessage] = list(state.get("messages", []))

    
    if not messages:
        messages = [HumanMessage(content="Hello")]

 
    response = agent_with_tools.invoke(messages)

    
    new_messages = messages + [response]
    return {"messages": new_messages}



def should_continue(state: MessagesState) -> str:
    messages: List[BaseMessage] = list(state.get("messages", []))
    if not messages:
        return END
    last = messages[-1]
    
    if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
        return "tools"
    
    return END

def sanitize_tool_output(state: MessagesState) -> Dict[str, Any]:
    """
    Inspects the last messages in the state, which are expected to be ToolMessages.
    If a tool message contains image data, it replaces the long base64 string
    with a short placeholder to keep the history clean.
    """
    messages = list(state.get("messages", []))
    sanitized_messages = []
    for msg in messages:
        if isinstance(msg, ToolMessage):
            # Create a new ToolMessage to avoid modifying the original in-place
            new_msg = ToolMessage(tool_call_id=msg.tool_call_id, name=msg.name, content=msg.content)
            if isinstance(new_msg.content, str) and new_msg.content.startswith("IMAGE_DATA::data:image"):
                new_msg.content = "[Image was generated and displayed to the user.]"
            sanitized_messages.append(new_msg)
        else:
            sanitized_messages.append(msg)
            
    return {"messages": sanitized_messages}

def create_agent_graph(system_prompt: str):
    workflow = StateGraph(MessagesState)

    def add_system_message(state: MessagesState) -> MessagesState:
        msgs = list(state.get("messages", []))
        msgs = _ensure_system_first(msgs, system_prompt)
        return {"messages": msgs}

    workflow.add_node("preprocess", add_system_message)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)
    workflow.add_node("sanitize_tools", sanitize_tool_output)
    workflow.set_entry_point("preprocess")
    workflow.add_edge("preprocess", "agent")
    workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    workflow.add_edge("tools", "agent")

    return workflow.compile()