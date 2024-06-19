from typing import List, Annotated

from fastapi import APIRouter, Body

from app.chain.chains import format_docs
from app.core.vectordb import vector_store
from app.schema import SearchKWArgs

search_router = APIRouter()

search_type_kwarg_map = {
    'similarity': ('k'),
    'similarity_score_threshold': ('score_threshold'),
    'mmr': ('k', 'score_threshold', 'fetch_k', 'lambda_mult')
}


@search_router.post("/search")
async def search(query: Annotated[str, Body()], search_type: str, search_kwargs: Annotated[SearchKWArgs, Body()]) -> List[str]:
    retriever = vector_store.as_retriever(search_type=search_type, search_kwargs=search_kwargs.model_dump(
        include=search_type_kwarg_map[search_type]))
    docs = await retriever.ainvoke(query)
    return [doc.page_content for doc in docs]

