# AI 做 T 训练 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增一个基于真实历史行情的 A 股「AI 做 T 训练」模块，支持股票/ETF 选择、历史回放、模拟买卖、规则教练和赛后复盘。

**Architecture:** 前端新增独立一级路由 `/training`，复用现有 `BasicLayout`、`ApiClient`、Element Plus 和 ECharts。后端新增独立 `training` 领域模块，训练会话、订单、回放游标和复盘报告都放在独立集合中，行情直接复用现有 `stocks` 和 `historical-data` 接口，避免改动分析链路。

**Tech Stack:** FastAPI, Pydantic v2, Motor/MongoDB, Vue 3, Pinia, Vue Router, Element Plus, ECharts, Python pytest

---

### Task 1: 训练领域数据模型与服务骨架

**Files:**
- Create: `app/models/training.py`
- Create: `app/services/training_service.py`
- Create: `tests/test_training_models.py`

- [ ] **Step 1: Write the failing test**

```python
from app.models.training import TrainingSessionCreate, TrainingAction


def test_training_session_defaults_and_fields():
    payload = TrainingSessionCreate(symbol="000001", start_date="2025-01-02")
    assert payload.initial_cash == 100000
    assert payload.total_days == 30
    assert payload.symbol == "000001"


def test_training_action_requires_buy_or_sell():
    action = TrainingAction(side="buy", quantity=100, price=10.5)
    assert action.side == "buy"
    assert action.quantity == 100
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_training_models.py -v`
Expected: FAIL because `app.models.training` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

Create Pydantic models for:
- `TrainingSessionCreate`
- `TrainingSessionResponse`
- `TrainingAction`
- `TrainingPosition`
- `TrainingReport`

Create `TrainingService` with empty method stubs for session creation, step query, trade submission and report generation.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_training_models.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/models/training.py app/services/training_service.py tests/test_training_models.py
git commit -m "feat: add training domain models"
```

### Task 2: 后端训练会话与回放 API

**Files:**
- Create: `app/routers/training.py`
- Modify: `app/main.py`
- Create: `tests/test_training_api.py`

- [ ] **Step 1: Write the failing test**

```python
from fastapi.testclient import TestClient


def test_create_training_session(client: TestClient):
    response = client.post(
        "/api/training/sessions",
        json={"symbol": "000001", "start_date": "2025-01-02", "initial_cash": 100000}
    )
    assert response.status_code == 200
    assert response.json()["success"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_training_api.py -v`
Expected: FAIL because `/api/training/sessions` is not mounted yet.

- [ ] **Step 3: Write minimal implementation**

Implement endpoints:
- `POST /api/training/sessions`
- `GET /api/training/sessions/{session_id}`
- `GET /api/training/sessions/{session_id}/step`
- `POST /api/training/sessions/{session_id}/actions`
- `POST /api/training/sessions/{session_id}/finish`
- `GET /api/training/sessions/{session_id}/report`

Mount the router in `app/main.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_training_api.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/routers/training.py app/main.py tests/test_training_api.py
git commit -m "feat: add training session api"
```

### Task 3: 前端训练页面与路由入口

**Files:**
- Create: `frontend/src/views/Training/index.vue`
- Create: `frontend/src/api/training.ts`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/components/Layout/TopNav.vue`
- Modify: `frontend/src/views/Dashboard/index.vue`

- [ ] **Step 1: Write the failing test**

```ts
import { routes } from '@/router'

test('training route exists', () => {
  expect(routes.some((route) => route.path === '/training')).toBe(true)
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && yarn type-check`
Expected: FAIL because `training` route and API module do not exist yet.

- [ ] **Step 3: Write minimal implementation**

Add a new `/training` route under `BasicLayout`.
Create a training page with four sections:
- 标的与参数
- 回放视图
- 买卖操作
- AI 教练与结果摘要

Expose a small `trainingApi` wrapper for the new backend endpoints.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && yarn type-check`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/Training/index.vue frontend/src/api/training.ts frontend/src/router/index.ts frontend/src/components/Layout/TopNav.vue frontend/src/views/Dashboard/index.vue
git commit -m "feat: add training ui and navigation"
```

### Task 4: 训练计算、规则教练与复盘报告

**Files:**
- Modify: `app/services/training_service.py`
- Create: `tests/test_training_logic.py`

- [ ] **Step 1: Write the failing test**

```python
from app.services.training_service import TrainingService


def test_hold_benchmark_uses_first_day_buy_then_hold():
    service = TrainingService()
    report = service.build_report(
        session={"initial_cash": 100000, "symbol": "000001"},
        trades=[],
        price_series=[{"close": 10.0}, {"close": 11.0}]
    )
    assert "buy_and_hold_return" in report
    assert "active_return" in report
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_training_logic.py -v`
Expected: FAIL because report and benchmark logic are not implemented yet.

- [ ] **Step 3: Write minimal implementation**

Implement:
- A股买卖规则计算
- 交易后资产更新
- 持有不动基准收益
- 最大回撤
- 规则教练建议生成
- 赛后复盘摘要

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_training_logic.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/training_service.py tests/test_training_logic.py
git commit -m "feat: implement training calculations and recap"
```

### Task 5: 最小端到端验证

**Files:**
- None new; verify the integrated flow

- [ ] **Step 1: Start backend and frontend**
- [ ] **Step 2: Create a training session via API**
- [ ] **Step 3: Fetch current visible step and submit a mock buy or sell**
- [ ] **Step 4: Finish the session and fetch the report**
- [ ] **Step 5: Run `cd frontend && yarn type-check`**
- [ ] **Step 6: Run `python -m py_compile app/routers/training.py app/services/training_service.py app/models/training.py`**

Expected: Training session can be created, progressed, traded, and summarized without exposing future data.

