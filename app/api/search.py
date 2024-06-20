from typing import List, Annotated, Tuple

from fastapi import APIRouter, Body

from app.core.vectordb import _search
from app.schema import SearchKWArgs

search_router = APIRouter()


@search_router.post("/search")
async def search(query: Annotated[str, Body()], search_type: str, search_kwargs: Annotated[SearchKWArgs, Body()]) -> \
        List[Tuple[str, float]] | List[str]:
    return await _search(query, search_type, search_kwargs, filter=None)
