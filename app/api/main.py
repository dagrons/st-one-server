import multiprocessing
from pathlib import Path

from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.api.api_key import api_key_router
from app.api.chat import chat_router
from app.api.user import user_router
from app.core.database import SessionLocal
from app.core.logger import logger_process, get_logger
from app.model.api_key import APIKey, APIAccess

app = FastAPI()
app.include_router(chat_router)
app.include_router(user_router)
app.include_router(api_key_router)


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

            if access_record:
                if access_record.access_count >= access_record.access_limit:
                    return JSONResponse(status_code=403, content={'message': 'API access limit reached'})
                access_record.access_count += 1
                session.add(access_record)
                await session.commit()

    response = await call_next(request)
    return response


@app.get("/health")
async def health():
    return {"message": "OK"}
