"""AI 做 T 训练服务。"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from datetime import datetime
from statistics import mean
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional
from uuid import uuid4

from app.models.training import (
    TrainingAdvice,
    TrainingAction,
    TrainingPosition,
    TrainingReport,
    TrainingReplayStep,
    TrainingSessionCreate,
    TrainingSessionResponse,
    TrainingSessionSummary,
)
from app.utils.timezone import now_tz


PriceSeriesRow = Dict[str, Any]
PriceSeriesLoader = Callable[[str, str, int], Awaitable[List[PriceSeriesRow]] | List[PriceSeriesRow]]


@dataclass
class _BenchmarkResult:
    final_value: float
    return_rate: float
    shares: int
    entry_price: float


class TrainingService:
    """训练会话与复盘的核心业务服务。"""

    _sessions: Dict[str, Dict[str, Any]] = {}

    def __init__(self, historical_loader: Optional[PriceSeriesLoader] = None, session_collection: Any = None) -> None:
        self._historical_loader = historical_loader
        self._session_collection = session_collection

    def _get_session_collection(self):
        if self._session_collection is not None:
            return self._session_collection
        try:
            from app.core.database import get_mongo_db

            db = get_mongo_db()
            return db.training_sessions
        except Exception:
            return None

    @staticmethod
    def _build_session_summary(state: Dict[str, Any]) -> TrainingSessionSummary:
        return TrainingSessionSummary(
            session_id=state["session_id"],
            symbol=state["symbol"],
            symbol_name=state.get("symbol_name"),
            market=state.get("market", "CN"),
            start_date=state["start_date"],
            end_date=str(state.get("end_date", "")),
            current_step=int(state.get("current_step", 0)),
            total_days=int(state.get("total_days", 30)),
            initial_cash=float(state.get("initial_cash", 100000)),
            cash=float(state.get("cash", 100000)),
            total_equity=float(state.get("total_equity", state.get("cash", 100000))),
            trade_count=int(state.get("trade_count", len(state.get("actions", [])))),
            status=state.get("status", "active"),
            note=state.get("note"),
            created_at=state.get("created_at", now_tz()),
            updated_at=state.get("updated_at", now_tz()),
        )

    def _serialize_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        doc = dict(state)
        doc.setdefault("created_at", now_tz())
        doc.setdefault("updated_at", now_tz())
        return doc

    def _hydrate_state(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        state = dict(doc)
        state.setdefault("actions", [])
        state.setdefault("equity_curve", [])
        state.setdefault("report", None)
        state.setdefault("current_step", 0)
        state.setdefault("cash", state.get("initial_cash", 100000))
        state.setdefault("trade_count", len(state.get("actions", [])))
        return state

    async def _persist_state(self, state: Dict[str, Any]) -> None:
        collection = self._get_session_collection()
        if collection is None:
            return
        doc = self._serialize_state(state)
        await collection.replace_one({"session_id": state["session_id"]}, doc, upsert=True)

    async def _load_session_state(self, session_id: str, owner_id: Optional[str] = None) -> Dict[str, Any]:
        state = self._sessions.get(session_id)
        if state and (owner_id is None or state.get("owner_id") == owner_id):
            return state

        collection = self._get_session_collection()
        if collection is None:
            raise KeyError(f"training session not found: {session_id}")
        query: Dict[str, Any] = {"session_id": session_id}
        if owner_id:
            query["owner_id"] = owner_id
        doc = await collection.find_one(query)
        if not doc:
            raise KeyError(f"training session not found: {session_id}")
        state = self._hydrate_state(doc)
        self._sessions[session_id] = state
        return state

    async def list_sessions(self, owner_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        collection = self._get_session_collection()
        if collection is None:
            sessions = [
                self._build_session_summary(state).model_dump()
                for state in self._sessions.values()
                if owner_id is None or state.get("owner_id") == owner_id
            ]
            sessions.sort(key=lambda item: item.get("updated_at") or item.get("created_at"), reverse=True)
            return sessions[:limit] if limit > 0 else sessions
        query: Dict[str, Any] = {}
        if owner_id:
            query["owner_id"] = owner_id
        cursor = collection.find(query).sort("updated_at", -1)
        if limit > 0:
            cursor = cursor.limit(limit)
        docs = await cursor.to_list(length=limit if limit > 0 else None)
        return [self._build_session_summary(self._hydrate_state(doc)).model_dump() for doc in docs]

    async def create_session(self, payload: TrainingSessionCreate, owner_id: str = "admin") -> TrainingSessionResponse:
        """创建一局训练。"""
        training_end_date = payload.end_date or self._derive_default_end_date()
        if payload.end_date or not payload.start_date:
            price_series = await self._load_price_series_until(payload.symbol, training_end_date, payload.total_days)
        else:
            price_series = await self._load_price_series(payload.symbol, payload.start_date, payload.total_days)
        if not price_series:
            raise ValueError("未找到可用于训练的历史行情数据")

        cash = float(payload.initial_cash)
        first_bar = price_series[0]
        last_bar = price_series[-1]
        start_date = str(first_bar.get("trade_date") or first_bar.get("date") or payload.start_date or "")
        end_date = str(last_bar.get("trade_date") or last_bar.get("date") or training_end_date)
        session_id = f"train_{uuid4().hex[:16]}"
        session = TrainingSessionResponse(
            session_id=session_id,
            symbol=payload.symbol,
            start_date=start_date,
            end_date=end_date,
            total_days=payload.total_days,
            initial_cash=cash,
            cash=cash,
            positions=[],
            realized_pnl=0,
            unrealized_pnl=0,
            total_equity=cash,
            trade_count=0,
            status="active",
        )

        self._sessions[session_id] = {
            **session.model_dump(),
            "owner_id": owner_id,
            "market": payload.market,
            "note": payload.note,
            "price_series": price_series,
            "current_step": 0,
            "actions": [],
            "equity_curve": [round(cash, 2)],
            "report": None,
            "current_price": float(first_bar.get("close", cash) or cash),
            "last_visible_date": start_date,
            "end_date": end_date,
        }
        await self._persist_state(self._sessions[session_id])
        return session

    async def get_session(self, session_id: str, owner_id: Optional[str] = None) -> TrainingSessionResponse:
        state = await self._load_session_state(session_id, owner_id=owner_id)
        return self._build_session_response(state)

    async def get_current_step(self, session_id: str, owner_id: Optional[str] = None) -> TrainingReplayStep:
        state = await self._load_session_state(session_id, owner_id=owner_id)
        price_series = state.get("price_series", [])
        current_step = int(state.get("current_step", 0))
        visible_bars = price_series[: current_step + 1] if price_series else []

        current_bar = visible_bars[-1] if visible_bars else {}
        closes = [self._as_float(bar.get("close")) for bar in visible_bars if self._as_float(bar.get("close")) is not None]
        volumes = [self._as_float(bar.get("volume")) for bar in visible_bars if self._as_float(bar.get("volume")) is not None]
        current_price = self._as_float(current_bar.get("close"))
        advice = self.generate_rule_advice(closes, volumes, current_step)
        session = self._build_session_response(state)

        is_finished = self._is_finished(state)
        trade_date = str(current_bar.get("trade_date") or current_bar.get("date") or state.get("start_date") or "")

        return self.build_replay_step(
            trade_date=trade_date,
            bar_index=current_step,
            visible_bars=visible_bars,
            is_finished=is_finished,
            current_price=current_price,
            advice=advice,
            session=session,
        )

    async def advance_session(self, session_id: str, owner_id: Optional[str] = None) -> TrainingReplayStep:
        state = await self._load_session_state(session_id, owner_id=owner_id)
        price_series = state.get("price_series", [])
        current_step = int(state.get("current_step", 0))
        max_step = max(len(price_series) - 1, 0)
        state["current_step"] = min(current_step + 1, max_step)
        state["updated_at"] = now_tz()
        self._refresh_mark_to_market(state)
        await self._persist_state(state)
        return await self.get_current_step(session_id, owner_id=owner_id)

    async def submit_action(self, session_id: str, action: TrainingAction | Dict[str, Any], owner_id: Optional[str] = None) -> TrainingSessionResponse:
        state = await self._load_session_state(session_id, owner_id=owner_id)
        if not isinstance(action, TrainingAction):
            action = TrainingAction.model_validate(action)
        current_price = self._get_current_price(state)
        if current_price <= 0:
            current_price = float(action.price)

        cash = float(state.get("cash", 0))
        realized_pnl = float(state.get("realized_pnl", 0))
        positions = [TrainingPosition(**item) for item in state.get("positions", [])]
        position = positions[0] if positions else TrainingPosition(
            symbol=str(state.get("symbol", "")),
            quantity=0,
            avg_cost=0.0,
            market_value=0.0,
            unrealized_pnl=0.0,
        )

        if action.side == "buy":
            gross = action.quantity * current_price
            commission = self._commission(gross)
            total_cost = gross + commission
            if total_cost > cash:
                raise ValueError("现金不足，无法完成买入")
            new_qty = position.quantity + action.quantity
            new_avg = ((position.quantity * position.avg_cost) + gross) / new_qty if new_qty else 0.0
            position.quantity = new_qty
            position.avg_cost = round(new_avg, 4)
            cash -= total_cost
        else:
            if action.quantity > position.quantity:
                raise ValueError("持仓不足，无法完成卖出")
            gross = action.quantity * current_price
            commission = self._commission(gross)
            stamp_duty = self._stamp_duty(gross)
            proceeds = gross - commission - stamp_duty
            realized_pnl += gross - commission - stamp_duty - (position.avg_cost * action.quantity)
            position.quantity -= action.quantity
            cash += proceeds

        position.market_value = round(position.quantity * current_price, 2)
        position.unrealized_pnl = round((current_price - position.avg_cost) * position.quantity, 2)
        state["positions"] = [position.model_dump()] if position.quantity > 0 else []
        state["cash"] = round(cash, 2)
        state["realized_pnl"] = round(realized_pnl, 2)
        state["unrealized_pnl"] = round(position.unrealized_pnl, 2)
        state["total_equity"] = round(state["cash"] + position.market_value, 2)
        state["trade_count"] = len(state.get("actions", [])) + 1
        state["actions"] = [*state.get("actions", []), {**action.model_dump(), "executed_price": round(current_price, 4)}]
        state["updated_at"] = now_tz()
        state["current_price"] = round(current_price, 4)
        self._append_equity_curve(state)
        await self._persist_state(state)
        return self._build_session_response(state)

    async def finish_session(self, session_id: str, owner_id: Optional[str] = None) -> Dict[str, Any]:
        state = await self._load_session_state(session_id, owner_id=owner_id)
        state["status"] = "finished"
        state["updated_at"] = now_tz()
        report = self._build_report_from_state(state)
        state["report"] = report
        await self._persist_state(state)
        return report

    async def get_report(self, session_id: str, owner_id: Optional[str] = None) -> Dict[str, Any]:
        state = await self._load_session_state(session_id, owner_id=owner_id)
        report = state.get("report")
        if isinstance(report, dict):
            return report
        return self._build_report_from_state(state)

    def build_replay_step(
        self,
        trade_date: str,
        bar_index: int,
        visible_bars: List[Dict[str, Any]],
        is_finished: bool = False,
        current_price: Optional[float] = None,
        advice: Optional[TrainingAdvice] = None,
        session: Optional[TrainingSessionResponse] = None,
    ) -> TrainingReplayStep:
        return TrainingReplayStep(
            trade_date=trade_date,
            bar_index=bar_index,
            visible_bars=visible_bars,
            is_finished=is_finished,
            current_price=current_price,
            advice=advice,
            session=session,
        )

    async def _load_price_series(self, symbol: str, start_date: str, total_days: int) -> List[PriceSeriesRow]:
        """按训练起点加载可见的历史行情。"""
        try:
            if self._historical_loader is not None:
                loaded = self._historical_loader(symbol, start_date, total_days)
                if inspect.isawaitable(loaded):
                    loaded = await loaded
                return self._normalize_price_series(loaded, total_days)

            from app.services.historical_data_service import get_historical_data_service

            service = await get_historical_data_service()
            rows = await service.get_historical_data(
                symbol=symbol,
                start_date=start_date,
                period="daily",
                limit=max(total_days * 8, 120),
            )
            return self._normalize_price_series(rows, total_days)
        except Exception:
            return []

    async def _load_price_series_until(self, symbol: str, end_date: str, total_days: int) -> List[PriceSeriesRow]:
        """按回放截止日向前加载训练所需的历史行情。"""
        try:
            if self._historical_loader is not None:
                fallback_start = end_date
                loaded = self._historical_loader(symbol, fallback_start, total_days)
                if inspect.isawaitable(loaded):
                    loaded = await loaded
                normalized = self._normalize_price_series(loaded, total_days)
                if len(normalized) > total_days:
                    normalized = normalized[-total_days:]
                return normalized

            from app.services.historical_data_service import get_historical_data_service

            service = await get_historical_data_service()
            rows = await service.get_historical_data(
                symbol=symbol,
                end_date=end_date,
                period="daily",
                limit=max(total_days * 8, 120),
            )
            normalized = self._normalize_price_series(rows, total_days)
            if len(normalized) > total_days:
                normalized = normalized[-total_days:]
            return normalized
        except Exception:
            return []

    @staticmethod
    def _derive_default_end_date() -> str:
        return now_tz().strftime("%Y-%m-%d")

    def generate_rule_advice(
        self,
        closes: List[float],
        volumes: List[float],
        current_index: int,
    ) -> TrainingAdvice:
        """根据当前可见行情生成规则教练建议。"""
        if not closes:
            return TrainingAdvice(
                trend_strength="弱",
                volume_change="平量",
                t_suitability="不适合",
                risk_level="高",
                chase_risk="高",
                dip_buy_suitability="低",
                position_range="0%-0%",
                reason="暂无可见行情，先观察。",
            )

        end = min(current_index + 1, len(closes))
        recent_closes = closes[max(0, end - 4):end]
        recent_volumes = volumes[max(0, end - 4):end] if volumes else []

        trend_strength = self._classify_trend(recent_closes)
        volume_change = self._classify_volume(recent_volumes)
        volatility = self._estimate_volatility(recent_closes)

        if trend_strength == "强" and volume_change == "放量":
            t_suitability = "谨慎"
            chase_risk = "高"
            dip_buy_suitability = "低"
            position_range = "0%-20%"
        elif trend_strength == "强" and volume_change in {"缩量", "平量"}:
            t_suitability = "可观察低吸"
            chase_risk = "低"
            dip_buy_suitability = "高"
            position_range = "20%-40%"
        else:
            t_suitability = "中性"
            chase_risk = "中"
            dip_buy_suitability = "中"
            position_range = "10%-30%"

        risk_level = "高" if volatility >= 0.03 else "中" if volatility >= 0.015 else "低"
        reason = self._build_advice_reason(trend_strength, volume_change, volatility)

        return TrainingAdvice(
            trend_strength=trend_strength,
            volume_change=volume_change,
            t_suitability=t_suitability,
            risk_level=risk_level,
            chase_risk=chase_risk,
            dip_buy_suitability=dip_buy_suitability,
            position_range=position_range,
            reason=reason,
        )

    def build_report(
        self,
        session: Dict[str, Any],
        trades: List[Dict[str, Any]],
        price_series: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """生成赛后复盘报告。"""
        initial_cash = float(session.get("initial_cash", 100000))
        final_cash = float(session.get("final_cash", session.get("cash", initial_cash)))
        final_equity = float(session.get("final_equity", session.get("total_equity", final_cash)))
        realized_pnl = float(session.get("realized_pnl", final_equity - initial_cash))
        unrealized_pnl = float(session.get("unrealized_pnl", 0))
        active_return = self._safe_return(final_equity, initial_cash)

        benchmark = self._buy_and_hold_benchmark(initial_cash, price_series)
        buy_and_hold_return = benchmark.return_rate
        excess_return = round(active_return - buy_and_hold_return, 6)

        equity_curve = self._resolve_equity_curve(session, price_series)
        max_drawdown = self._max_drawdown(equity_curve)

        good_trades, bad_trades = self._classify_trades(trades, price_series)
        advice = self._build_recap_advice(active_return, buy_and_hold_return, len(trades), max_drawdown)

        report = TrainingReport(
            session_id=str(session.get("session_id", "")),
            symbol=str(session.get("symbol", "")),
            start_date=str(session.get("start_date", "")),
            end_date=self._resolve_end_date(session, price_series),
            final_cash=round(final_cash, 2),
            final_equity=round(final_equity, 2),
            realized_pnl=round(realized_pnl, 2),
            unrealized_pnl=round(unrealized_pnl, 2),
            active_return=round(active_return, 6),
            buy_and_hold_return=round(buy_and_hold_return, 6),
            excess_return=excess_return,
            trade_count=int(session.get("trade_count", len(trades))),
            max_drawdown=max_drawdown,
            good_trades=good_trades,
            bad_trades=bad_trades,
            advice=advice,
        )
        return report.model_dump()

    def _require_session(self, session_id: str) -> Dict[str, Any]:
        state = self._sessions.get(session_id)
        if not state:
            raise KeyError(f"training session not found: {session_id}")
        return state

    def _build_session_response(self, state: Dict[str, Any]) -> TrainingSessionResponse:
        positions = [TrainingPosition(**item) for item in state.get("positions", [])]
        return TrainingSessionResponse(
            session_id=state["session_id"],
            symbol=state["symbol"],
            symbol_name=state.get("symbol_name"),
            market=state.get("market", "CN"),
            start_date=state["start_date"],
            end_date=str(state.get("end_date", "")),
            current_step=int(state.get("current_step", 0)),
            total_days=int(state.get("total_days", 30)),
            initial_cash=float(state.get("initial_cash", 100000)),
            cash=float(state.get("cash", 100000)),
            positions=positions,
            realized_pnl=float(state.get("realized_pnl", 0)),
            unrealized_pnl=float(state.get("unrealized_pnl", 0)),
            total_equity=float(state.get("total_equity", state.get("cash", 100000))),
            trade_count=int(state.get("trade_count", len(state.get("actions", [])))),
            status=state.get("status", "active"),
            created_at=state.get("created_at", now_tz()),
            updated_at=state.get("updated_at", now_tz()),
        )

    def _refresh_mark_to_market(self, state: Dict[str, Any]) -> None:
        current_price = self._get_current_price(state)
        positions = [TrainingPosition(**item) for item in state.get("positions", [])]
        if positions:
            position = positions[0]
            position.market_value = round(position.quantity * current_price, 2)
            position.unrealized_pnl = round((current_price - position.avg_cost) * position.quantity, 2)
            state["positions"] = [position.model_dump()] if position.quantity > 0 else []
            state["unrealized_pnl"] = round(position.unrealized_pnl, 2)
            state["total_equity"] = round(float(state.get("cash", 0)) + position.market_value, 2)
        else:
            state["unrealized_pnl"] = 0.0
            state["total_equity"] = round(float(state.get("cash", 0)), 2)
        self._append_equity_curve(state)

    def _append_equity_curve(self, state: Dict[str, Any]) -> None:
        equity_curve = state.setdefault("equity_curve", [])
        if isinstance(equity_curve, list):
            equity_curve.append(round(float(state.get("total_equity", 0)), 2))

    def _get_current_price(self, state: Dict[str, Any]) -> float:
        price_series = state.get("price_series", [])
        current_step = int(state.get("current_step", 0))
        if not price_series:
            return float(state.get("current_price", 0) or 0)
        index = min(current_step, len(price_series) - 1)
        row = price_series[index]
        price = self._as_float(row.get("close"))
        if price is None:
            price = self._as_float(state.get("current_price"))
        return float(price or 0)

    def _normalize_price_series(self, rows: Any, total_days: int) -> List[PriceSeriesRow]:
        normalized: List[PriceSeriesRow] = []
        if not rows:
            return normalized

        for row in rows:
            if not isinstance(row, dict):
                continue
            close = self._as_float(row.get("close"))
            trade_date = str(row.get("trade_date") or row.get("date") or row.get("time") or "").strip()
            if not trade_date or close is None:
                continue
            normalized.append(
                {
                    "trade_date": trade_date,
                    "open": self._as_float(row.get("open")),
                    "high": self._as_float(row.get("high")),
                    "low": self._as_float(row.get("low")),
                    "close": close,
                    "volume": self._as_float(row.get("volume") or row.get("vol")),
                    "amount": self._as_float(row.get("amount") or row.get("turnover")),
                }
            )

        normalized.sort(key=lambda item: item["trade_date"])
        if len(normalized) > max(total_days * 8, 120):
            normalized = normalized[-max(total_days * 8, 120):]
        return normalized

    @staticmethod
    def _commission(amount: float) -> float:
        return round(max(amount * 0.0003, 5.0), 2)

    @staticmethod
    def _stamp_duty(amount: float) -> float:
        return round(amount * 0.001, 2)

    @staticmethod
    def _safe_return(final_value: float, initial_value: float) -> float:
        if initial_value <= 0:
            return 0.0
        return round((final_value - initial_value) / initial_value, 6)

    @staticmethod
    def _classify_trend(closes: List[float]) -> str:
        if len(closes) < 2:
            return "弱"
        change = (closes[-1] - closes[0]) / closes[0] if closes[0] else 0
        if change >= 0.02:
            return "强"
        if change <= -0.02:
            return "弱"
        return "中"

    @staticmethod
    def _classify_volume(volumes: List[float]) -> str:
        if len(volumes) < 2:
            return "平量"
        avg_prev = mean(volumes[:-1]) if len(volumes) > 1 else volumes[-1]
        latest = volumes[-1]
        if avg_prev <= 0:
            return "平量"
        ratio = latest / avg_prev
        if ratio >= 1.15:
            return "放量"
        if ratio <= 0.85:
            return "缩量"
        return "平量"

    @staticmethod
    def _estimate_volatility(closes: List[float]) -> float:
        if len(closes) < 2:
            return 0.0
        base = closes[0] or 1.0
        high = max(closes)
        low = min(closes)
        return abs(high - low) / base

    @staticmethod
    def _build_advice_reason(trend_strength: str, volume_change: str, volatility: float) -> str:
        if trend_strength == "强" and volume_change == "放量":
            return "趋势强且放量，适合谨慎跟随，不宜追高过猛。"
        if trend_strength == "强" and volume_change == "缩量":
            return "趋势仍强但量能收缩，可等待低吸机会。"
        if volatility >= 0.03:
            return "波动偏大，做 T 机会和风险同时提高。"
        return "当前信号中性，先看趋势和量能是否继续配合。"

    def _buy_and_hold_benchmark(self, initial_cash: float, price_series: List[Dict[str, Any]]) -> _BenchmarkResult:
        if not price_series:
            return _BenchmarkResult(final_value=initial_cash, return_rate=0.0, shares=0, entry_price=0.0)

        first_close = float(price_series[0].get("close", 0) or 0)
        last_close = float(price_series[-1].get("close", first_close) or first_close)
        if first_close <= 0:
            return _BenchmarkResult(final_value=initial_cash, return_rate=0.0, shares=0, entry_price=0.0)

        lot_size = 100
        shares = int(initial_cash // (first_close * lot_size)) * lot_size
        if shares <= 0:
            return _BenchmarkResult(final_value=initial_cash, return_rate=0.0, shares=0, entry_price=first_close)

        commission = self._commission(shares * first_close)
        cash_left = initial_cash - shares * first_close - commission
        final_value = cash_left + shares * last_close
        return _BenchmarkResult(
            final_value=round(final_value, 2),
            return_rate=round((final_value - initial_cash) / initial_cash, 6),
            shares=shares,
            entry_price=first_close,
        )

    @staticmethod
    def _resolve_equity_curve(session: Dict[str, Any], price_series: List[Dict[str, Any]]) -> List[float]:
        equity_curve = session.get("equity_curve")
        if isinstance(equity_curve, list) and equity_curve:
            return [float(v) for v in equity_curve]

        closes = [float(item.get("close", 0) or 0) for item in price_series if item.get("close") is not None]
        if closes:
            return closes
        return [float(session.get("final_equity", session.get("initial_cash", 0)))]

    @staticmethod
    def _max_drawdown(values: Iterable[float]) -> float:
        peak = 0.0
        max_dd = 0.0
        for raw in values:
            value = float(raw)
            if value <= 0:
                continue
            peak = max(peak, value)
            if peak <= 0:
                continue
            drawdown = (peak - value) / peak
            max_dd = max(max_dd, drawdown)
        return round(max_dd, 6)

    @staticmethod
    def _classify_trades(trades: List[Dict[str, Any]], price_series: List[Dict[str, Any]]) -> tuple[list[Dict[str, Any]], list[Dict[str, Any]]]:
        if not trades:
            return [], []

        closes = [float(item.get("close", 0) or 0) for item in price_series if item.get("close") is not None]
        avg_close = mean(closes) if closes else 0.0
        good: list[Dict[str, Any]] = []
        bad: list[Dict[str, Any]] = []
        for trade in trades:
            side = str(trade.get("side", "")).lower()
            price = float(trade.get("executed_price", trade.get("price", 0)) or 0)
            item = dict(trade)
            item["judgement"] = "good" if (side == "buy" and price <= avg_close) or (side == "sell" and price >= avg_close) else "bad"
            if item["judgement"] == "good":
                good.append(item)
            else:
                bad.append(item)
        return good, bad

    @staticmethod
    def _build_recap_advice(
        active_return: float,
        buy_and_hold_return: float,
        trade_count: int,
        max_drawdown: float,
    ) -> str:
        lines: List[str] = []
        if active_return > buy_and_hold_return:
            lines.append("主动做 T 跑赢了持有不动。")
        else:
            lines.append("主动做 T 没有跑赢持有不动。")

        if trade_count >= 10:
            lines.append("交易次数偏多，先减少无效进出。")
        elif trade_count <= 3:
            lines.append("交易次数较少，可以继续观察节奏。")

        if max_drawdown >= 0.08:
            lines.append("回撤偏大，仓位控制需要更严格。")
        elif max_drawdown <= 0.03:
            lines.append("回撤控制较稳。")

        return " ".join(lines)

    def _build_report_from_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        price_series = state.get("price_series", [])
        current_step = int(state.get("current_step", 0))
        visible_price_series = price_series[: current_step + 1] if price_series else []
        if not visible_price_series and price_series:
            visible_price_series = price_series[:1]

        if visible_price_series:
            last_bar = visible_price_series[-1]
            state["final_cash"] = round(float(state.get("cash", 0)), 2)
            state["final_equity"] = round(
                float(state.get("cash", 0)) + float(state.get("positions", [{}])[0].get("market_value", 0) if state.get("positions") else 0),
                2,
            )
            state["end_date"] = str(last_bar.get("trade_date") or last_bar.get("date") or state.get("start_date") or "")
        else:
            state["final_cash"] = round(float(state.get("cash", 0)), 2)
            state["final_equity"] = round(float(state.get("total_equity", state.get("cash", 0))), 2)
            state["end_date"] = str(state.get("start_date") or "")

        return self.build_report(
            session=state,
            trades=state.get("actions", []),
            price_series=visible_price_series,
        )

    @staticmethod
    def _resolve_end_date(session: Dict[str, Any], price_series: List[Dict[str, Any]]) -> str:
        if session.get("end_date"):
            return str(session.get("end_date"))
        if price_series:
            last_bar = price_series[-1]
            return str(last_bar.get("trade_date") or last_bar.get("date") or session.get("start_date", ""))
        return str(session.get("start_date", ""))

    @staticmethod
    def _as_float(value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _is_finished(self, state: Dict[str, Any]) -> bool:
        price_series = state.get("price_series", [])
        current_step = int(state.get("current_step", 0))
        total_days = int(state.get("total_days", 30))
        max_step = max(min(total_days, len(price_series)) - 1, 0) if price_series else max(total_days - 1, 0)
        return current_step >= max_step
