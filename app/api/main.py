import multiprocessing
import uuid
from pathlib import Path

from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi_offline import FastAPIOffline
from sqlalchemy import select

from app.api.api_key import api_key_router
from app.api.chat import chat_router
from app.api.search import search_router
from app.core.database import SessionLocal
from app.core.logger import logger_process, get_nonblocking_logger
from app.model.api_key import APIKey, APIAccess

app = FastAPIOffline()
app.include_router(chat_router)
app.include_router(search_router)
app.include_router(api_key_router)

origins = ["http://localhost:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event('startup')
async def startup_handler():
    log_queue = multiprocessing.Queue()
    log_file = str(Path('.').resolve() / 'application.log')
    log_process = multiprocessing.Process(target=logger_process, args=(log_queue, log_file))
    log_process.start()
    app.state.log_queue = log_queue
    app.state.log_process = log_process
    app.state.logger = get_nonblocking_logger(log_queue)
    app.state.logger.info({'event': 'on_app_startup', 'data': {'message': 'logger installed'}})


@app.on_event('shutdown')
async def shutdown_handler():
    app.state.log_queue.put(None)
    app.state.log_process.join()
    app.state.logger.info({'event': 'on_app_shutdown', 'data': {'message': 'logger uninstalled'}})


@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    path = request.url.path
    if path not in ["/restricted-api"]:
        response = await call_next(request)
        return response
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return JSONResponse(status_code=400, content={"message": "Missing API Key"})

    async with SessionLocal() as session:
        async with session.begin():
            result = await session.execute(select(APIKey).filter(APIKey.key == api_key))
            api_key_record = result.scalar()

            if not api_key_record:
                return JSONResponse(status_code=401, content={'message': "Invalid API Key"})

            result = await session.execute(
                select(APIAccess).filter(APIAccess.api_key == api_key, APIAccess.api_name == path))
            access_record = result.scalar()

            if not access_record or access_record.access_count >= access_record.access_limit:
                return JSONResponse(status_code=403, content={'message': 'API access limit reached'})
            access_record.access_count += 1
            session.add(access_record)
            await session.commit()

    response = await call_next(request)
    return response


@app.middleware("http")
async def trace_id_middleware(request: Request, call_next):
    trace_id = str(uuid.uuid4())
    request.state.trace_id = trace_id
    response = await call_next(request)
    response.headers['X-Trace-Id'] = trace_id
    return response


@app.get("/health")
async def health():
    return {"message": "OK"}
