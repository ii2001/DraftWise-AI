"""Connect to the MCP server via stdio and actually call its tool."""
import json
import os
import sys
from .champions import catalog

async def fetch_catalog() -> tuple[dict,str]:
    if os.getenv('DRAFTWISE_MCP_DISABLED')=='1':
        return catalog(),'local_disabled'
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        params=StdioServerParameters(
            command=sys.executable,args=['-m','app.mcp_server'],
            env={**os.environ, 'PYTHONUNBUFFERED':'1'})
        async with stdio_client(params) as (read,write):
            async with ClientSession(read,write) as session:
                await session.initialize()
                result=await session.call_tool('get_champion_catalog',{})
                if result.isError:
                    raise RuntimeError('MCP tool returned an error')
                structured=getattr(result,'structuredContent',None)
                if isinstance(structured,dict):
                    value=structured.get('result',structured)
                    if isinstance(value,dict) and 'champions' in value:
                        return value,'mcp_stdio'
                for item in result.content:
                    if getattr(item,'type','')=='text':
                        value=json.loads(item.text)
                        if 'champions' in value:return value,'mcp_stdio'
                raise ValueError('MCP invalid tool payload')
    except ImportError:
        # Teaching/demo mode only when package unavailable.
        return catalog(),'local_mcp_unavailable'
