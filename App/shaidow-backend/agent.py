# agent.py

from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI

from tools import all_tools


class AgentState(TypedDict):
    """
    Defines the state of our agent. It's a dictionary that holds the conversation history.
    'messages' is a sequence of BaseMessage objects that will be appended to.
    """
    messages: Sequence[BaseMessage]

agent_model = ChatOpenAI(model="gpt-4o-mini", temperature=0, streaming=True)


agent_with_tools = agent_model.bind_tools(all_tools)

tool_node = ToolNode(all_tools)

def should_continue(state: AgentState) -> str:
    """
    Conditional edge logic. Determines whether to continue the loop or end.
    - If the last message is a tool call, we continue to the 'tools' node.
    - Otherwise (it's a regular AI response), we end the graph execution.
    """
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END

def call_model(state: AgentState) -> dict:
    """
    The primary node of the graph. It invokes the agent's core model.
    It takes the current conversation state and returns the model's response.
    """
    response = agent_with_tools.invoke(state["messages"])
    # The response will be an AIMessage, possibly with tool_calls.
    return {"messages": [response]}

def create_agent_graph():
    """
    Factory function to create and compile the LangGraph agent.
    """
    workflow = StateGraph(AgentState)

    
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)

    
    workflow.set_entry_point("agent")

    
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",  
            END: END           
        },
    )

   
    workflow.add_edge("tools", "agent")

    
    agent_graph = workflow.compile()
    
    return agent_graph