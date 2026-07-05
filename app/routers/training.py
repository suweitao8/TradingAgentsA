"""AI 做 T 训练 API 路由。"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.core.response import ok
from app.models.training import TrainingAction, TrainingSessionCreate
from app.services.training_service import TrainingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/training", tags=["training"])
training_service = TrainingService()


@router.post("/sessions")
async def create_session(payload: TrainingSessionCreate):
    try:
        session = await training_service.create_session(payload)
        return ok(session.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("创建训练会话失败: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    try:
        session = await training_service.get_session(session_id)
        return ok(session.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/sessions/{session_id}/step")
async def get_step(session_id: str):
    try:
        step = await training_service.get_current_step(session_id)
        return ok(step.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/sessions/{session_id}/actions")
async def submit_action(session_id: str, payload: TrainingAction):
    try:
        session = await training_service.submit_action(session_id, payload)
        return ok(session.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/sessions/{session_id}/advance")
async def advance_session(session_id: str):
    try:
        step = await training_service.advance_session(session_id)
        return ok(step.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/sessions/{session_id}/finish")
async def finish_session(session_id: str):
    try:
        report = await training_service.finish_session(session_id)
        return ok(report)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/sessions/{session_id}/report")
async def get_report(session_id: str):
    try:
        report = await training_service.get_report(session_id)
        return ok(report)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
