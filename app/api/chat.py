import json
from typing import Annotated

from fastapi import APIRouter, Body, Request, Depends
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessageChunk

from app.chain.chains import rag_chain

chat_router = APIRouter(prefix="/chat")


def get_logger(request: Request):
    return request.app.state.logger


@chat_router.post("/generate")
async def stream_chat(model: str, prompt: str, chat_history: Annotated[list[tuple[str, str]], Body()],
                      logger=Depends(get_logger)):
    chain = await rag_chain(model)

    async def stream_gen():
        async for event in chain.astream_events({'question': prompt, 'history': chat_history}, version="v1"):
            kind = event['event']
            name = event['name']
            if name == "my_llm":
                if kind == "on_llm_start":
                    logger.info({'event': kind, 'data': event['data']['input']['prompts']})
                elif kind == "on_chat_model_start":
                    logger.info({'event': kind, 'data': event['data']['input']})
                elif kind == "on_llm_stream":
                    token = event['data']['chunk']
                    logger.info({'event': kind, 'data': token})
                    yield token
                elif kind == "on_chat_model_stream":
                    token = event['data']['chunk'].content
                    logger.info({'event': kind, 'data': token})
                    yield token
                elif kind == "on_llm_end":
                    logger.info({'event': kind, 'data': event['data']['output']['generations']})
                elif kind == "on_chat_model_end":
                    final_output = [[chunk['text'] for chunk in generation] for generation in event['data']['output']['generations']]
                    logger.info({'event': kind, 'data': final_output})
            elif name == "Docs":
                if kind == "on_retriever_end":
                    documents = []
                    for doc in event['data']['output']['documents']:
                        documents.append(doc.page_content)
                    documents = json.dumps(documents)
                    logger.info({'event': kind, 'data': documents})
                    yield f"<docs>{documents}</docs>"

    return StreamingResponse(stream_gen())
