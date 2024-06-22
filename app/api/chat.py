import json
from typing import Annotated

from fastapi import APIRouter, Body, Depends
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_logger, get_trace_id
from app.chain.chains import rag_chain

chat_router = APIRouter(prefix="/chat")


@chat_router.post("/generate")
async def stream_chat(model: str, prompt: str, chat_history: Annotated[list[tuple[str, str]], Body()],
                      logger=Depends(get_logger), trace_id=Depends(get_trace_id)):
    chain = await rag_chain(model)

    async def stream_gen():
        async for event in chain.astream_events({'question': prompt, 'history': chat_history}, version="v1"):
            kind = event['event']
            name = event['name']
            if name == "my_llm":
                if kind == "on_llm_start":
                    logger.info({'event': kind, 'data': event['data']['input']['prompts'], 'trace_id': trace_id})
                elif kind == "on_chat_model_start":
                    logger.info({'event': kind, 'data': event['data']['input'], 'trace_id': trace_id})
                elif kind == "on_llm_stream":
                    token = event['data']['chunk']
                    logger.info({'event': kind, 'data': token, 'trace_id': trace_id})
                    yield token
                elif kind == "on_chat_model_stream":
                    token = event['data']['chunk'].content
                    logger.info({'event': kind, 'data': token, 'trace_id': trace_id})
                    yield token
                elif kind == "on_llm_end":
                    logger.info({'event': kind, 'data': event['data']['output']['generations'], 'trace_id': trace_id})
                elif kind == "on_chat_model_end":
                    final_output = [[chunk['text'] for chunk in generation] for generation in
                                    event['data']['output']['generations']]
                    logger.info({'event': kind, 'data': final_output, 'trace_id': trace_id})
            elif name == "Docs":
                if kind == "on_retriever_end":
                    documents = []
                    for doc in event['data']['output']['documents']:
                        documents.append(doc.page_content)
                    documents = json.dumps(documents)
                    logger.info({'event': kind, 'data': documents, 'trace_id': trace_id})
                    yield f"<docs>{documents}</docs>"

    return StreamingResponse(stream_gen())
