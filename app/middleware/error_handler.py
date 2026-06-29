"""
错误处理中间件

统一 API 错误响应信封，与 app.core.response 的项目标准对齐：
    {success: False, message: <中文说明>, code: <HTTP 状态码>, timestamp: ...}

前端 frontend/src/api/request.ts 的 ApiResponse 与 handleBusinessError 期望此结构。
保留 HTTP 状态码语义（400/403/404/500），前端按 status 走对应错误分支，
400 分支会读取 body.message 显示给用户。
"""

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
from typing import Callable

from app.core.response import fail
from app.utils.timezone import now_tz

logger = logging.getLogger(__name__)


async def _error_response(request: Request, status_code: int, message: str) -> JSONResponse:
    """构造统一错误响应（信封对齐 response.fail，额外带 request_id 便于排查）"""
    request_id = getattr(request.state, "request_id", None)
    body = fail(message=message, code=status_code)
    body["request_id"] = request_id
    return JSONResponse(status_code=status_code, content=body)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """全局错误处理中间件

    捕获路由链路中未被处理的异常，按类型分级返回标准化错误响应。
    注意：FastAPI/Starlette 路由内主动抛出的 HTTPException 由 exception_handler 处理，
    不会进到这里；本中间件主要兜底 ValueError/PermissionError/FileNotFoundError 及未知异常。
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            return await self.handle_error(request, exc)

    async def handle_error(self, request: Request, exc: Exception) -> JSONResponse:
        """根据异常类型返回不同的错误响应"""
        request_id = getattr(request.state, "request_id", "unknown")

        logger.error(
            f"请求异常 - ID: {request_id}, "
            f"路径: {request.url.path}, "
            f"方法: {request.method}, "
            f"异常: {str(exc)}",
            exc_info=True
        )

        # 分级处理：业务异常返回对应语义的状态码
        if isinstance(exc, ValueError):
            return await _error_response(request, 400, str(exc) or "请求参数错误")

        if isinstance(exc, PermissionError):
            return await _error_response(request, 403, "权限不足")

        if isinstance(exc, FileNotFoundError):
            return await _error_response(request, 404, "请求的资源不存在")

        # Starlette/FastAPI 的 HTTPException（如 404 路由不存在）落到这里时按其状态码透传
        if isinstance(exc, StarletteHTTPException):
            status_code = exc.status_code or 500
            detail = exc.detail if isinstance(exc.detail, str) else "请求错误"
            return await _error_response(request, status_code, detail)

        # 未知异常
        return await _error_response(request, 500, "服务器内部错误，请稍后重试")
