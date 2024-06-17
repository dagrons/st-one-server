import multiprocessing
from pathlib import Path
from typing import Annotated, Tuple, List

import fastapi
from fastapi import FastAPI, Body
from requests import Request
from sqlalchemy import select
from starlette.responses import JSONResponse, StreamingResponse

from app.chain.chains import get_simple_chain, get_retrieval_chain, get_with_history_retrieval_chain
from app.core.database import SessionLocal
from app.core.logger import logger_process, get_logger
from app.model.acl import APIKey, APIAccess

app = FastAPI()


@app.on_event('startup')
async def startup_handler():
    log_queue = multiprocessing.Queue()
    log_file = str(Path('.').resolve() / 'application.log')
    log_process = multiprocessing.Process(target=logger_process, args=(log_queue, log_file))
    log_process.start()
    app.state.log_queue = log_queue
    app.state.log_process = log_process
    app.state.logger = get_logger(log_queue)


@app.on_event('shutdown')
async def shutdown_handler():
    app.state.log_queue.put(None)
    app.state.log_process.join()


@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return JSONResponse(status_code=400, content={"message": "Missing API Key"})

    async with SessionLocal() as session:
        async with session.begin():
            result = await session.execute(select(APIKey).filter(APIKey.key == api_key))
            api_key_record = result.scalar()

            if not api_key_record:
                return JSONResponse(status_code=401, content={'message': "Invalid API Key"})

            path = request.url.path
            result = await session.execute(
                select(APIAccess).filter(APIAccess.api_key == api_key, APIAccess.api_name == path))
            access_record = result.scalar()

            if access_record:
                if access_record.access_count >= access_record.access_limit:
                    return JSONResponse(status_code=403, content={'message': 'API access limit reached'})
                access_record.access_count += 1
                session.add(access_record)
                await session.commit()

    response = await call_next(request)
    return response


@app.get("/open-api")
async def open_api():
    return {"message": "This is an open API"}


@app.get("/restricted-api")
async def restricted_api():
    return {"message": "This is a restricted API"}


@app.post("/stream_chat")
async def stream_chat(model: str, prompt: str, chat_history: Annotated[list[tuple[str, str]], Body()],
                      enable_rag: bool):
    if len(chat_history) == 0 and not enable_rag:
        chain = get_simple_chain(model)
        data = prompt
    if enable_rag and len(chat_history) == 0:
        chain = get_retrieval_chain(model)
        data = {'question': prompt}
    else:
        chain = get_with_history_retrieval_chain(model)
        data = {'question': prompt, 'history': chat_history}

    async def stream_gen():
        async for event in chain.astream_events(data, version="v1"):
            kind = event['event']
            name = event['name']
            if name == "my_llm":
                if kind == "on_llm_stream":
                    yield event['data']['chunk']
    return StreamingResponse(stream_gen())
