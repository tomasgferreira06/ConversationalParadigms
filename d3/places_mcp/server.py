"""Places MCP server (MCP protocol layer only; all logic lives in places_service).

Two tools over stdio: search_place and get_distance_between_places. Importing this
module does not start anything; the server only runs from main().

Usage:
    uv run python d3/places_mcp/server.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

sys.path.insert(0, str(Path(__file__).resolve().parent))

from places_service import PlacesError, PlacesService  # noqa: E402

service = PlacesService()

mcp = MCPServer("places", log_level="WARNING")


@mcp.tool(
    name="search_place",
    description=(
        "Procura a localização geográfica de um local, monumento, estabelecimento ou endereço e devolve "
        "coordenadas e dados de localização (até 3 candidatos, pela ordem do OpenStreetMap/Nominatim). "
        "Use esta tool quando for necessário saber onde fica um local. country_code é opcional "
        "(código ISO de duas letras, por exemplo 'pt')."
    ),
)
def search_place(query: str, country_code: str | None = None) -> dict[str, Any]:
    try:
        return service.search_place(query, country_code)
    except PlacesError as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool(
    name="get_distance_between_places",
    description=(
        "Calcula a distância geodésica em linha reta entre dois locais depois de os resolver "
        "geograficamente. Não representa distância rodoviária, pedonal ou tempo de viagem. "
        "country_code é opcional (código ISO de duas letras, por exemplo 'pt')."
    ),
)
def get_distance_between_places(origin: str, destination: str, country_code: str | None = None) -> dict[str, Any]:
    try:
        return service.get_distance_between_places(origin, destination, country_code)
    except PlacesError as exc:
        raise ToolError(str(exc)) from exc


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
