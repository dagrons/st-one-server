from fastapi import Request


def get_logger(request: Request):
    return request.app.state.logger


def get_trace_id(request: Request):
    return request.state.trace_id
