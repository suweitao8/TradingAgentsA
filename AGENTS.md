# 项目代理指引

> 本文件是 TradingAgentsA 项目所有 AI 会话工具（ZCode / CodeX / Claude Code）共用的**唯一权威规则源**。
> 适用于「中文增强版 TradingAgents」——基于 Python(FastAPI) + Vue3 + MongoDB + Redis 的多智能体股票分析平台。

## 规则源与同步

- **AGENTS.md 是唯一权威规则源**（所有会话工具都读，已纳入 git），只放**通用工作流**规则。
- **项目特定领域知识放 `docs/` 下对应文档**（架构、部署、数据源等），按任务路由表按需读取，不强制每次会话全读。
- **CLAUDE.md 是 AGENTS.md 的完整同步副本**（供 Claude Code 读取，本地保留、不进 git，在 `.gitignore` 中排除），由 `.githooks/post-commit` 自动同步，无需手动维护。
- **`MEMORY.md` 是 AI 个人反思日志**（本地保留、不进 git），记录反复踩过的环境陷阱和浪费模式。每次新会话第一件事就是读它。
- 本项目明确允许 CLAUDE.md 与 AGENTS.md 并存（覆盖 `/md` 默认的"禁止并存"判断）。

### 工具使用

本项目所有任务由**会话工具独立完成**——开发、修 bug、重构、规则优化、查询，全部自己做，走 Superpowers 流程。所有会话工具共用本文件，工作流完全一致，不区分具体工具。

### 项目级 Skills（`.agents/skills/`）

以下技能安装在本项目 `.agents/skills/` 下，随 git 走，换机器/clone 后自动可用。按任务类型按需激活：

| Skill | 来源 | 触发场景 | 说明 |
|-------|------|---------|------|
| `full-output-enforcement` | animcg 迁移 | 任何要求完整代码输出的任务 | 禁止占位符（`// ...`/`// TODO`），强制完整交付，token 超限时分片处理 |
| `modern-python` | [trailofbits/skills](https://github.com/trailofbits/skills) | 新建 Python 项目/脚本、配置 ruff/pytest、工具链迁移 | uv/ruff/ty 现代工具链。**本项目当前用 pip+3.10，此 skill 作升级参考，勿擅自迁移** |
| `fastapi-router-py` | [microsoft/skills](https://github.com/microsoft/skills) | 新建 FastAPI 路由、CRUD 端点、加鉴权 | 已适配本项目结构（`app/routers/`、MongoDB） |
| `pydantic-models-py` | [microsoft/skills](https://github.com/microsoft/skills) | 定义 API 请求/响应 schema、Pydantic v2 模型 | 多模型模式（Base/Create/Update/Response/InDB），已适配 MongoDB |

> 用户级 skills（`~/.agents/skills/`，37 个通用工作流 skill 如 tdd-workflow、systematic-debugging、git-workflow 等）全局可用，不在此重复列出。

### 任务路由（按需读取领域知识）

| 任务关键词 | 必读 AGENTS.md 章节 | 按需读 docs/ 章节 | 可用 Skill |
|------------|-------------------|-------------------------------|-----------|
| 任何开发任务 | 全文（本文件精简版） | — | `full-output-enforcement` |
| 新建 FastAPI 路由/CRUD | — | — | `fastapi-router-py` |
| 定义 API schema/Pydantic 模型 | — | — | `pydantic-models-py` |
| 新建 Python 脚本/配 ruff/pytest | — | — | `modern-python`（升级参考，勿擅自迁移） |
| 改 LLM 适配器/Provider | — | `docs/llm/`、`docs/technical/` | — |
| 加/改数据源 | — | `docs/development/ADD_NEW_DATA_SOURCE.md`、`docs/data/` | — |
| 改 MongoDB/数据库 | — | `docs/deployment/database/` | — |
| 改配置/Settings | — | `docs/configuration/`、`docs/SETTINGS_MERGE.md` | — |
| 前端 Vue/样式 | — | `docs/frontend/` | — |
| 部署/Docker | — | `docs/deployment/`、`docs/BUILD_GUIDE.md` | — |
| 写测试/验证 | 验证与收尾 | `docs/development/DEVELOPMENT_SETUP.md` | `modern-python`（testing.md） |

### 工作流硬规则（最高优先级）

- 所有**代码**开发任务都必须先创建隔离 worktree；禁止在主工作区（`main` 分支）直接动手改代码。
- **配置、文档、规则文件**（AGENTS.md / docs / .gitignore / Dockerfile 等）允许在 main 上直接修改。
- worktree 内允许提交，但任何任务结束时都必须把提交合并回 `main`，然后删除当前 worktree 并执行 `git worktree prune`。
- 完成收尾前，回复只报告结果、验证证据和收尾状态，不主动追加可选建议。
- 本节优先于下文任何历史残留措辞；凡与本节冲突的内容，一律以本节为准。

## 核心铁律（最高优先级，绝不可违反）

1. **禁止在 main 分支或主工作区直接修改代码** — 仓库主工作区（`D:\Github\TradingAgentsA`）只允许只读检查、配置/文档/规则改动，与收尾阶段的合并/推送/清理确认；任何代码改动（`app/`、`tradingagents/`、`cli/`、`web/`、`scripts/`、`tests/`、`utils/`、`frontend/src/` 下的源码）都必须先进入独立 worktree，在 worktree 内完成
2. **强制中文输出** — 所有对话、解释、计划、提交信息、注释必须使用中文（代码标识符用英文）
3. **服务器永远不能停** — 用户正在浏览器中使用开发服务器（backend 8000 / frontend 3000），任何操作都不允许导致服务器长时间不可用
4. **合并推送后立即删 worktree** — `git merge` → `git push origin main` → 立即删除本会话隔离 worktree → `git worktree prune`，四步连续执行不可分割；push 成功不等于完成，`git worktree list` 仍残留当前 worktree 就禁止报告"已完成"
5. **没有验证证据不能声称完成** — 禁止"应该可以""理论上没问题"等措辞，必须实际运行验证
6. **开发完成后必须自我反思** — 将反复出现的同类问题通过修改本文件或 MEMORY.md 永久预防，反思在合并前执行
7. **会话开始必读 MEMORY.md** — MEMORY.md 记录了 AI 反复犯错的具体操作和环境陷阱，跳过必读会重复浪费时间

## 基本约定

- 所有对话、说明、总结、错误解释、代码注释和提交信息尽量使用中文；技术名词可保留英文，建议附中文解释。
- 仓库内源码、配置与文档统一使用 UTF-8 编码。
- **双许可证边界**：`app/`（FastAPI 后端）和 `frontend/`（Vue 前端）是**专有代码**（需商业授权）；`tradingagents/`、`cli/`、`web/`、`scripts/`、`tests/`、`utils/` 是 Apache 2.0 开源代码。改动 `app/`/`frontend/` 时注意许可证约束。
- **依赖声明在 `pyproject.toml`**（不要用 `requirements.txt`，已废弃）。前端依赖在 `frontend/package.json`（用 yarn，不用 npm）。
- **配置源是 `app/core/config.py` 的 `Settings`**（pydantic-settings 读 `.env`），不要在代码里硬编码密钥、端口、数据库连接串；新增配置项时同步更新 `.env.example`。
- **数据库**：MongoDB（主库，motor 异步驱动）+ Redis（缓存/队列）。MongoDB 库名由主版本号 + 实例标签派生（`MONGODB_DATABASE_SCOPE`），改版本隔离逻辑要极其谨慎，详见 `docs/deployment/database/`。
- 规则、规范、文档、代理指引类请求，直接修改本文件，不走完整开发链路。
- 修改本文件时，先通读全文，合并重复条目、删除冗余表述、统一术语和结构，再保存。
- 动手前必须先用 `git rev-parse --show-toplevel` 和 `git worktree list` 双重确认当前 shell 是否在本次会话的隔离 worktree；若仍在主目录、仍在 `main` 分支、或 worktree list 里看不到本次会话的隔离 worktree，一律先创建/切换到 worktree 再允许任何代码写入。
- 在通过上述检查之前，禁止执行任何会写代码文件的动作。
- 仓库已配置工作区守卫：
  - **`.githooks/pre-commit` 守卫**：在主工作区、main 分支上提交**代码文件**会被直接拦截；worktree 内提交或只改配置/文档/规则文件放行。需执行 `git config core.hooksPath .githooks` 启用（每台机器一次性）。
  - **`.claude/hooks/branch-guard-hook.js`**：Claude Code 的 Edit/Write 工具在 main 分支上写代码文件会被拦截（PreToolUse hook）。
- 并行开发时每个会话都应使用独立工作区，避免互相踩改动。每个对话只能管理自己创建的隔离 worktree，绝对不能删除、改动或清理其他正在进行中的 worktree。

## 开发流程（Superpowers）

### 四步流程

所有产生代码 diff 的任务，走完整 Superpowers 流程：

1. **规划** — 写计划文档（建 worktree 后在 worktree 内写，或直接用 EnterPlanMode）。明确改动范围、影响面、验证方式。
2. **执行** — 在 worktree 分支内实现改动，手术式修改，最小改动量。
3. **验证** — 跑统一验证清单（见下），收集验证证据。
4. **收尾** — 合并回 main → push → 删 worktree → prune → 自我反思。

> 简单任务（解释项目结构、查数据、单点查询、回答问题、改配置/文档/规则）：直接做，不需要走 worktree 流程。不确定复杂度时按开发任务处理（走 worktree），宁可多走流程。

### 任务路由

| 用户说什么 | 起始动作 |
|-----------|---------|
| "实现/加功能/修 bug/重构" | 进 worktree → 写计划 → 改 → 验证 → 收尾 |
| "改规则/审计 AGENTS.md" | 直接改本文件 → 审查 → 提交 |
| "查一下/看看/解释" | 只读检查，不改不提交 |
| "跑一下测试" | 只读执行验证 |

### 统一验证清单

按改动类型分层验证（**Python 适配，取代旧的 tsc/npm build**）：

| 改动类型 | 验证命令 | 说明 |
|---------|---------|------|
| Python 后端（`app/`、`tradingagents/`） | `python -m py_compile <file>` 或 `python -m pytest tests/ -x -q` | 语法检查 + 单测（集成测试默认跳过） |
| 服务端 API 链路 | `curl http://localhost:8000/api/health` + 实际接口调用 | 必须跑真实服务端验证，不能只靠单测 |
| 前端 Vue（`frontend/src/`） | `cd frontend && yarn type-check` | vue-tsc 类型检查 |
| 前端构建 | `cd frontend && yarn build` | 仅大改动或发版前 |
| 前端样式/交互 | 浏览器实际查看 | 需 dev server 在跑 |
| 数据库/Mongo | `mongosh` 连接查询确认 | 改 schema 后必须验证 |

- 集成测试：`python -m pytest -m integration tests/`（需真实环境，默认跳过）。
- **禁止"编译通过就声称完成"**：服务端链路改动必须用真实接口调用验证。

### Subagent-Driven 子任务卡住时的处理

子任务 BLOCKED 时，不要在子任务里空转或编造，立即回到主会话汇报卡点、附上已尝试的方法和错误信息，由主会话决定是换方案、加资源还是终止。

## `md` 入口

`/md` 是项目规则文件统一入口（修改/审计/反思 AGENTS.md）。仅当用户显式调用 `/md` 时触发：

- "加规则""改规则""删除 xxx" → 直接编辑 AGENTS.md
- "审计""检查质量""评分" → 只审查出报告
- "记录教训""revise""更新规则" → 从会话提取经验写回

每次修改 AGENTS.md 后强制触发质量审查和优化（流程见下文「自我反思」）。修改在 main 上直接进行（属配置/规则类），提交后 `.githooks/post-commit` 自动同步到 CLAUDE.md。

## 自我反思与流程优化（每次开发后强制执行）

### 强制卡点：反思必须在合并之前

合并回 main 之前，必须完成自我反思。反思结果写入 MEMORY.md（操作陷阱）或本文件（工作流规则）。

### 必答六问

每次开发完成后回答：

1. **根因** — 这次问题/改动的根本原因是什么？
2. **历史** — 是否是反复出现的同类问题？（查 MEMORY.md）
3. **流程** — 现有流程是否有漏洞导致这次问题？
4. **预防** — 能否通过加一条规则永久避免？
5. **浪费** — 这次有没有浪费时间的操作？（无效命令、绕弯路）
6. **Token** — 有没有浪费 token 的模式？（通读大文件、重复搜索）

### 改完规则文件必须审查（强制闭环）

修改 AGENTS.md 后立即六维度自检：命令可执行性 / 架构一致性 / 模式重复 / 简洁性 / 时效性 / 可执行性。发现问题立即优化。审查不通过的标志：与现有规则矛盾、与现有内容重复超 30%、命令不可执行、通用建议非项目特定、字数增长超 20% 但无实质价值。

### 简化原则

规则应该随经验积累**越来越准确**，而不是越来越长。每次改完检查：能否合并条目？能否删除冗余？能否用更精确的表述？

## 行为准则

### 1. 编码前先思考
动手前先研究现有实现和约定，避免重复造轮子。涉及第三方集成（数据源、LLM provider）先看 `docs/` 对应文档和现有 adapter 实现。

### 2. 简单优先
能用最小改动解决的问题，不要过度设计。先让它工作，再让它正确，最后才考虑优化。

### 3. 手术式修改
只改需要改的部分，不顺便重构无关代码。diff 越小越容易审查、越不容易引入回归。

### 4. 目标驱动执行
始终盯着用户的目标，不被沿途的技术好奇心带偏。用户要的是结果，不是过程展示。

### 5. 图片/视频识别
模型不能直接"看"图片/视频。需要识别图片内容时，使用 `mcp__zai-mcp-server__*` 系列 MCP 工具（analyze_image / extract_text_from_screenshot 等），不要凭文件名猜测图片内容。

## 验证与收尾

- 每次完成必须给出验证证据（命令 + 输出），不接受"应该可以"。
- 分层验证见上文「统一验证清单」。
- 收尾流程见下文「worktree 管理 → 收尾总纲」。
- 完成收尾前，回复只报告结果、验证证据、收尾状态，不主动追加可选建议。

## Token 节省规范（用户 token 预算有限，强制遵守）

### 1. 探索任务委派给 Explore subagent（省得最多）
需要扫多个文件/目录、跨多个模块找东西时，委派给 Explore agent，只回收结论，不回收文件原文。

### 2. 结构化查询优先于通读文件
- 用 CodeGraph MCP（`mcp__codegraph__*`：semantic_search / context / where / fn_impact 等）做符号级查询，优于 Grep 通读。
- 用 `ast_query` / `list_functions` 等结构化查询优于 Read 整个文件。
- 只在定位到具体文件/符号后才 Read 具体片段。

### 3. 命令输出主动截断
长命令输出用 `head` / `tail` / 限制行数，不要把几千行日志原样回灌。

### 4. 输出简洁化
回复只讲结论和证据，不铺陈推理过程（规则文件和提交信息例外，需完整）。验证证据贴关键输出行，不贴全文。

### 5. Headroom MCP（工具输出压缩）
大段工具输出（搜索结果、日志、JSON）用 `mcp__headroom__headroom_compress` 压缩后存引用，后续用 `headroom_retrieve` 取回。

### 6. Bug 诊断的最短路径（禁止绕弯）
- 先看报错信息本身，定位到文件:行号，再决定下一步。不要一上来就通读整个模块。
- 复现优先：先稳定复现，再定位根因，再修复。不要在不能复现的情况下盲改。
- 改一处验证一处，不要攒一堆改动一起验证（出问题无法定位是哪处）。

## 服务器管理

### 核心原则：服务器永远不能停
用户正在浏览器中使用开发服务器。任何操作不允许导致 backend/frontend 长时间不可用。

### 开发任务完成后自动判断重启
- 只改前端 → frontend dev server（Vite HMR）自动热更新，无需重启。
- 改了后端 Python 代码 → uvicorn `--reload` 自动重载；若改了启动配置/依赖/环境变量，需重启 backend。
- 重启策略：先启动新实例确认可用，再停旧实例（无缝重启）。

### 基本信息
| 服务 | 端口 | 启动命令 |
|------|------|---------|
| 后端 FastAPI | 8000 | `python -m uvicorn app.main:app --reload --port 8000` |
| 前端 Vue | 3000 | `cd frontend && yarn dev`（Vite，代理 `/api` → 8000） |
| MongoDB | 27017 | docker / 本地服务 |
| Redis | 6379（docker 宿主机映射 6380） | docker / 本地服务 |
| 旧版 Streamlit | 8501 | `python -m streamlit run web/app.py`（legacy，新功能用 FastAPI/Vue） |
| Docker 全栈 | — | `docker-compose up -d` |

- 后端健康检查：`curl http://localhost:8000/api/health`
- 前端 dev server 代理 `/api` 到后端 8000（见 `frontend/vite.config.ts`）。

## worktree 管理

### 创建流程

主工作区路径固定 `D:\Github\TradingAgentsA`，worktree 统一放 `D:\Github\TradingAgentsA\.worktrees\<task-name>`。

```bash
# 1. 从 main 建隔离 worktree
git worktree add .worktrees/<task-name> -b feat/<task-name> main
cd .worktrees/<task-name>

# 2. Python：worktree 共享主仓库的 venv，无需重新安装依赖
#    （直接用主仓库 .venv 的解释器，或在 worktree 内建独立 venv）

# 3. 前端：worktree 内 node_modules 较大，二选一
#    a) 软链主仓库 node_modules（Windows 用 junction）：
#       cmd //c "mklink /J .worktrees\<task-name>\frontend\node_modules ..\..\frontend\node_modules"
#    b) 或在 worktree 内单独 yarn install（耗时但隔离）

# 4. 确认在 worktree 内
git rev-parse --show-toplevel   # 应显示 .worktrees\<task-name> 路径
git worktree list               # 应能看到本次会话的 worktree
```

- Python 后端无需在 worktree 内重新 `pip install`（共享主仓库 venv 即可，依赖变更时在主仓库装一次）。
- 前端 `node_modules` 大，优先软链主仓库的，避免每个 worktree 都 yarn install。

### 收尾总纲（最高优先级，不可跳过）

任务完成后必须执行：**合并 → 推送 → 删 worktree → prune**，四步连续不可分割。

### 收尾清单（merge/push 后唯一权威顺序）

1. 在 worktree 内确认所有改动已提交（`git status` 干净）
2. 切回主工作区：`cd D:\Github\TradingAgentsA`
3. `git checkout main`
4. `git merge --no-ff feat/<task-name>`（保留分支历史）
5. `git push origin main`
6. `git worktree remove .worktrees/<task-name>`（删 worktree 目录）
7. `git branch -d feat/<task-name>`（删功能分支）
8. `git worktree prune`（清理残留）
9. `git worktree list` 确认无残留 → 才能报告"已完成"

### 删除步骤（安全检查）

删 worktree 前三重确认：
- worktree 内 `git status` 干净（无未提交改动）
- 已成功 `git merge` 到 main
- 已成功 `git push origin main`

满足三条才执行 `git worktree remove`。若 remove 报目录被占用（Windows 文件锁），先确认无进程占用（dev server / python 进程），再重试或手动删。

### 任务完成标准（全部满足才能报告完成）

- ✅ 代码已合并到 main 并 push 成功
- ✅ worktree 已删除，`git worktree list` 无残留
- ✅ 验证证据已提供（命令 + 输出）
- ✅ 自我反思已完成（写入 MEMORY.md 或本文件）

## 质量与提交

- 修 bug 前先定位根因，不要症状式修补（治标不治本）。
- 改动最小化：只改需要改的，不顺便重构无关代码。
- 提交前 `git fetch` + 检查是否有冲突。
- 完成四条件：编译/类型检查通过 + 功能验证通过 + 无回归 + 验证证据已提供。
- rebase 冲突：先理解冲突原因再解决，不要盲目 accept current/Incoming。

## 项目常用规范

### 版本号管理
- 版本号在 `VERSION` 文件（当前 `v1.0.1`），`pyproject.toml` 的 `version` 字段与之保持一致。
- 发版时同步更新两处 + 写 `docs/releases/` 版本说明 + 打 `v*` tag（触发 CI 构建镜像）。

### 临时调试脚本管理
- 临时验证/调试脚本放 `scripts/debug/`，不要堆在根目录或 `tests/` 顶层。
- `tests/` 下很多 `test_*.py` / `debug_*.py` 是可直接 `python tests/xxx.py` 运行的脚本，非纯 pytest 用例，注意区分。

### 常用命令

```bash
# Python 后端
pip install -e .                # 或 uv pip install -e .，安装项目（开发模式）
python -m uvicorn app.main:app --reload --port 8000   # 启动后端 dev server
python -m pytest tests/ -x -q  # 跑单测（集成测试默认跳过）
python -m pytest -m integration tests/  # 跑集成测试
python -m py_compile <file>     # 快速语法检查

# 前端
cd frontend
yarn install
yarn dev          # Vite dev server (3000)
yarn type-check   # vue-tsc 类型检查
yarn build        # 生产构建
yarn lint         # eslint --fix

# Docker 全栈
docker-compose up -d                       # 启动所有服务
docker-compose --profile management up -d  # 含 redis-commander/mongo-express
docker-compose logs -f backend             # 看后端日志

# 数据库
mongosh "mongodb://<user>:<pass>@localhost:27017/<db>?authSource=admin"  # 连 Mongo
mongodump --uri="..." --out=backups/       # 备份
mongorestore --uri="..." backups/          # 恢复
```

### UTF-8 安全编辑
- 所有文件 UTF-8 编码。注意 `.gitignore` 等文件勿被编辑器改成 UTF-16/带 BOM。
- Windows 环境下 git hook 内避免用 `cp`/`copy`（会静默失败），改用 `python -c "import shutil;..."`。

### 不要用只读 agent 做编辑任务
Explore / 只读 agent 不能写文件。需要写文件的任务由主会话执行。

### 遇到耗时操作必须先提醒用户
跑全量测试、yarn install、docker build、大量 LLM 调用等耗时操作前，先告知用户预计耗时，再执行。

## 安全保护

### Git 危险操作保护
执行 `git reset --hard` / `git push --force` / `git clean -fd` / 删分支前：
- 先 `git log` / `git stash list` 检查是否有未推送的提交或未保存的改动。
- 强制推送前确认不会覆盖他人提交（本项目主开发为单人，但仍需谨慎）。

### 数据库备份
改 MongoDB schema / 做破坏性数据迁移前：
```bash
mongodump --uri="$MONGODB_URI" --out=backups/backup_$(date +%Y-%m-%d_%H-%M-%S)
```
备份成功后才执行迁移。

### 任务卡住排查
- backend 不响应：`curl http://localhost:8000/api/health` → 看日志 `docker-compose logs backend` 或本地日志。
- 前端接口 404/500：先确认 backend 在跑（端口 8000），再看 vite 代理配置。
- MongoDB 连不上：检查 `.env` 的 `MONGODB_*` 配置和 docker 服务状态。
- Redis 连不上：同上，检查 `REDIS_*` 配置。
- LLM 调用失败：检查对应 provider 的 API KEY 和 `*_BASE_URL`。

## 沟通方式

- 不展示可视化 diff（终端环境无意义），直接讲改了什么。
- 不主动询问"这样设计可以吗"——方案明确直接执行，执行完报告结果。
- 报告完成时只讲：做了什么 + 验证证据 + 收尾状态，不追加可选建议。

## 全局禁止行为汇总

- ❌ 跳过 Superpowers 流程直接在 main 改代码
- ❌ 在 main 分支或主工作区直接改代码文件（配置/文档/规则除外）
- ❌ 合并推送后不删 worktree（`git worktree list` 残留）
- ❌ 没有验证证据就声称完成（"编译通过"≠"完成"）
- ❌ 服务端链路改动只跑单测不跑真实接口验证
- ❌ 在代码里硬编码密钥、端口、数据库连接串（应走 `.env` + Settings）
- ❌ 用 `requirements.txt` 声明依赖（已废弃，用 `pyproject.toml`）
- ❌ 前端用 npm（本项目用 yarn）
- ❌ 盲目合并上游 `TauricResearch/TradingAgents`（本项目是选择性吸收，见 `docs/maintenance/`）
- ❌ 改完 AGENTS.md 不做质量审查
- ❌ 用只读 agent 做需要写文件的任务
- ❌ 耗时操作不提前告知用户
