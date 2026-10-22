"""Real MCP Tool/Resource service; start via `python -m app.mcp_server`."""
from mcp.server.fastmcp import FastMCP
from .champions import catalog, lookup

mcp = FastMCP('DraftWise Champion Intelligence')

@mcp.tool()
def get_champion_catalog() -> dict:
    """Return curated champion roles, damage types, crowd control and engage scores."""
    return catalog()

@mcp.tool()
def get_champion_detail(champion_id:str) -> dict:
    """Look up one champion's curated metadata by Data Dragon ID."""
    return lookup().get(champion_id, {'error':'champion not found'})

@mcp.resource('draftwise://metadata-policy')
def metadata_policy() -> str:
    return '특성 정보는 수작업 데모 데이터이며 승률, 메타 티어, 실시간 상성을 보장하지 않습니다.'

if __name__=='__main__':
    mcp.run(transport='stdio')
