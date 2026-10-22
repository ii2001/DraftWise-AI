"""Actual LangGraph StateGraph when installed; sequential dev fallback otherwise."""
from typing import Any, TypedDict
from .mcp_client import fetch_catalog
from .scoring import DraftRequest,draft_analysis
from .llm import explain

class DraftState(TypedDict, total=False):
    request: dict[str,Any]
    roster: list[dict[str,Any]]
    mcp_mode: str
    analysis: dict[str,Any]
    explanation: str
    llm_mode: str
    trace: list[str]

async def retrieve(state:DraftState) -> dict:
    data,mode=await fetch_catalog()
    return {'roster':data['champions'],'mcp_mode':mode,
            'trace':state.get('trace',[])+['mcp_retrieve']}

async def score(state:DraftState) -> dict:
    req=DraftRequest.model_validate(state['request'])
    return {'analysis':draft_analysis(req,state['roster']),
            'trace':state.get('trace',[])+['rule_scoring']}

async def narrate(state:DraftState) -> dict:
    req=DraftRequest.model_validate(state['request'])
    explanation,mode=await explain(req,state['analysis'])
    return {'explanation':explanation,'llm_mode':mode,
            'trace':state.get('trace',[])+['llm_explanation']}

async def run_agent(req:DraftRequest) -> dict:
    state={'request':req.model_dump(),'trace':['validate_input']}
    try:
        from langgraph.graph import StateGraph, START, END
    except ImportError:
        # Clear mode label, not represented as a LangGraph run.
        for node in (retrieve,score,narrate):
            state.update(await node(state))
        state['graph_mode']='sequential_fallback_langgraph_unavailable'
    else:
        builder=StateGraph(DraftState)
        builder.add_node('retrieve',retrieve)
        builder.add_node('score',score)
        builder.add_node('explain',narrate)
        builder.add_edge(START,'retrieve')
        builder.add_edge('retrieve','score')
        builder.add_edge('score','explain')
        builder.add_edge('explain',END)
        graph=builder.compile()
        state=await graph.ainvoke(state)
        state['graph_mode']='langgraph'
    return {**state['analysis'], 'explanation':state['explanation'],
            'trace':state['trace'],'llm_mode':state['llm_mode'],
            'mcp_mode':state['mcp_mode'],'graph_mode':state['graph_mode']}
