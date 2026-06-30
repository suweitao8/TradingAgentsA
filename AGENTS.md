# 项目代理指引

> 本文件是 TradingAgentsA 项目所有 AI 会话工具（ZCode / CodeX / Claude Code）共用的**唯一权威规则源**。
> 适用于「中文增强版 TradingAgents」——基于 Python(FastAPI) + Vue3 + MongoDB + Redis 的多智能体股票分析平台。

## 规则源与同步

- **AGENTS.md 是唯一权威规则源**（所有会话工具都读，已纳入 git），只放**通用工作流**规则。
- **项目特定领域知识放 `docs/` 下对应文档**（架构、部署、数据源、上游同步等），按任务路由表按需读取，不强制每次会话全读。
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

### 领域知识路由（按需读取 docs）

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
| 上游同步 | — | `docs/maintenance/upstream-sync.md`、`docs/maintenance/manual-upstream-absorption-checklist.md` | — |
| 写测试/验证 | 验证与收尾 | `docs/development/DEVELOPMENT_SETUP.md` | `modern-python`（testing.md） |

## 工作流硬规则（最高优先级）

- 所有**代码**开发任务都必须先创建隔离 worktree；禁止在主工作区（`main` 分支）直接动手改代码。
- **配置、文档、规则文件**（AGENTS.md / docs / .gitignore / Dockerfile 等）允许在 main 上直接修改。
- worktree 内允许提交，但任何任务结束时都必须完成**收尾清单**（见「worktree 管理 → 收尾清单」），合并回 main、删除 worktree。
- 完成收尾前，回复只报告结果、验证证据和收尾状态，不主动追加可选建议。
- 本节优先于下文任何历史残留措辞；凡与本节冲突的内容，一律以本节为准。

## 核心铁律（最高优先级，绝不可违反）

1. **禁止在 main 分支或主工作区直接修改代码** — 仓库主工作区（`D:\Github\TradingAgentsA`）只允许只读检查、配置/文档/规则改动，与收尾阶段的合并/推送/清理确认；任何代码改动（`app/`、`tradingagents/`、`cli/`、`web/`、`scripts/`、`tests/`、`utils/`、`frontend/src/` 下的源码）都必须先进入独立 worktree，在 worktree 内完成
2. **强制中文输出** — 所有对话、解释、计划、提交信息、注释必须使用中文（代码标识符用英文）
3. **服务器永远不能停** — 用户正在浏览器中使用开发服务器（backend 8000 / frontend 3000），任何操作都不允许导致服务器长时间不可用
4. **收尾四步连续不可分割** — `git merge` → `git push origin main` → 删除本会话隔离 worktree → `git worktree prune`，详见「worktree 管理 → 收尾清单」。push 成功不等于完成，`git worktree list` 仍残留当前 worktree 就禁止报告"已完成"
5. **没有验证证据不能声称完成** — 禁止"应该可以""理论上没问题"等措辞，验证标准见「开发流程 → 统一验证清单」
6. **开发完成后必须自我反思** — 将反复出现的同类问题通过修改本文件或 MEMORY.md 永久预防，反思在合并前执行
7. **会话开始必读 MEMORY.md** — MEMORY.md 记录了 AI 反复犯错的具体操作和环境陷阱，跳过必读会重复浪费时间

## 基本约定

- **双许可证边界**：`app/`（FastAPI 后端）和 `frontend/`（Vue 前端）是**专有代码**（需商业授权）；`tradingagents/`、`cli/`、`web/`、`scripts/`、`tests/`、`utils/` 是 Apache 2.0 开源代码。改动 `app/`/`frontend/` 时注意许可证约束。
- **依赖声明在 `pyproject.toml`**（不要用 `requirements.txt`，已废弃）。前端依赖在 `frontend/package.json`（用 yarn，不用 npm）。
- **配置源是 `app/core/config.py` 的 `Settings`**（pydantic-settings 读 `.env`），不要在代码里硬编码密钥、端口、数据库连接串；新增配置项时同步更新 `.env.example`。
- **数据库**：MongoDB（主库，motor 异步驱动）+ Redis（缓存/队列）。MongoDB 库名由主版本号 + 实例标签派生（`MONGODB_DATABASE_SCOPE`），改版本隔离逻辑要极其谨慎，详见 `docs/deployment/database/`。
- 仓库内源码、配置与文档统一使用 UTF-8 编码。
- 规则、规范、文档、代理指引类请求，直接修改本文件，不走完整开发链路。
- 修改本文件时，先通读全文，合并重复条目、删除冗余表述、统一术语和结构，再保存。
- **worktree 状态验证**（动手前 + 创建后两个时机）：见「worktree 管理 → 创建流程」的三重验证命令。未通过验证前，禁止执行任何会写代码文件的动作。
- **`git worktree add` 返回成功 ≠ worktree 已注册**：Windows 下存在 add 提示"HEAD is now at ... done"但实际未注册的情况，此时 shell 若停留在失效路径上，后续所有 git 命令会回退到主工作区 .git，`git rm`/`git add -A`/`git commit` 会作用在游离状态甚至误暂存主工作区的会话前改动。因此 add 之后必须立即三重验证（见创建流程第4步），任一不过即停止、清理物理目录后重新 add。
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
4. **收尾** — 执行「worktree 管理 → 收尾清单」的完整流程，然后自我反思。

> 简单任务（解释项目结构、查数据、单点查询、回答问题、改配置/文档/规则）：直接做，不需要走 worktree 流程。不确定复杂度时按开发任务处理（走 worktree），宁可多走流程。

### 改动规模与流程开销匹配（分层执行，避免过度流程）

不同改动按规模走不同流程，不强制每个改动都走完整 Superpowers 四步（规划→执行→验证→收尾）：

| 改动规模 | 流程 | 说明 |
|---------|------|------|
| **纯工具函数**（`utils/` 正则/字符串/字段映射） | worktree → `py_compile` + 单测 → 收尾 | 省去计划文档，单测覆盖即可 |
| **单文件 bug 修复**（改一个 router/一个 service） | worktree → py_compile → curl API 验证 → 收尾 | 不需要写计划，但服务端链路必须真实接口验证 |
| **新功能/多文件/架构改动** | 完整 Superpowers 四步流程 | 规划→执行→验证→收尾 |
| **规则/规范/文档** | 直接在 main 改，不走 worktree | 符合工作流硬规则豁免 |

### 任务路由

| 用户说什么 | 起始动作 |
|-----------|---------|
| "实现/加功能/修 bug/重构" | 进 worktree → 写计划 → 改 → 验证 → 收尾 |
| "改规则/审计 AGENTS.md" | 直接改本文件 → 审查 → 提交 |
| "查一下/看看/解释" | 只读检查，不改不提交 |
| "跑一下测试" | 只读执行验证 |

### 统一验证清单

按改动类型分层验证（**Python 适配，取代旧的 tsc/npm build**）。主验证必须做、补充验证按需、禁止列明确什么手段不能用：

| 改动类型 | 主验证（必须做） | 补充验证 | 禁止 |
|---------|---------|---------|------|
| **Python 纯函数/工具**（`utils/`、数据转换、正则、字段映射） | `python -m py_compile <file>` | `python -m pytest tests/xxx.py -q`（有对应单测时） | ❌ 起服务验证纯函数 |
| **服务端 API 链路**（`app/routers/`、`app/services/`、`tradingagents/` 数据源/分析流程） | **curl 真实 API**（`http://localhost:8000/api/...`）+ **mongosh 直查落库结果** | `python -m py_compile`（辅助语法检查） | ❌ 用浏览器验证服务端逻辑；❌ 只 py_compile 就声称完成 |
| **前端 Vue 逻辑/类型**（`frontend/src/` 数据绑定、props、composable） | `cd frontend && yarn type-check` | HMR（用户浏览器实时看到） | ❌ AI 主动开浏览器自动化截图验证 |
| **前端视觉/CSS/布局/交互** | `cd frontend && yarn type-check`（确保不破坏类型） | **默认不开浏览器**，用户反馈问题后再排查 | ❌ AI 主动开浏览器做前端验证 |
| **前端构建**（发版/大改动） | `cd frontend && yarn build` | — | ❌ 小改动也跑全量 build |
| **数据库 schema/Mongo** | `mongosh` 连接查询确认 | — | ❌ 只看代码不查库确认 |

**核心原则：本项目服务端逻辑（API/分析/数据源）占比大，默认走 curl API + mongosh 直查；前端改动只跑 type-check，UI 问题等用户反馈再排查，AI 不主动开浏览器。**

- 集成测试：`python -m pytest -m integration tests/`（需真实环境，默认跳过）。

### 强制规则：服务端链路改动必须跑真实服务端验证（不只停在 py_compile）

`py_compile` 只能验证语法，验证不了"集成到真实流程后是否生效"。因此：

- 改动涉及服务端链路（`app/routers/`、`app/services/`、`tradingagents/` 数据源、分析流程、API 路由）时，改完必须**调一次真实服务端功能验证**，不能只 py_compile 就声称完成。
- **标准验证方式**：backend 在端口 8000 运行，用 `curl`（中文参数用 Python `urllib` 避免 URL 编码问题）调用对应 API，再用 `mongosh` 直查落库结果确认改动生效。
- `py_compile` 只能作辅助（确认语法/导入路径），不能替代真实服务端调用。
- 纯工具函数改动（如 `utils/` 下正则、字符串处理）允许只用 `python -m pytest` 单测，不需要起服务。

（具体的"禁止"手段见上方验证分层表的"禁止"列。）

### Subagent-Driven 子任务卡住时的处理

子任务 BLOCKED 时，不要在子任务里空转或编造，立即回到主会话汇报卡点、附上已尝试的方法和错误信息，由主会话决定是换方案、加资源还是终止。

## `md` 入口

`/md` 是项目规则文件统一入口（修改/审计/反思 AGENTS.md）。仅当用户显式调用 `/md` 时触发：

- "加规则""改规则""删除 xxx" → 直接编辑 AGENTS.md
- "审计""检查质量""评分" → 只审查出报告
- "记录教训""revise""更新规则" → 从会话提取经验写回

每次修改 AGENTS.md 后强制触发质量审查和优化（流程见下文「自我反思」）。修改在 main 上直接进行（属配置/规则类），提交后 `.githooks/post-commit` 自动同步到 CLAUDE.md。

## 自我反思与流程优化（每次开发后强制执行）

**目标：每个 bug 只允许出现一次。同类问题第二次出现，必须修改本文件或 MEMORY.md 永久预防；第三次视为严重流程缺陷。**

### 强制卡点：反思必须在合并之前

执行顺序（硬约束）：
1. 代码改完 + 验证通过
2. **执行必答六问**（必须实际输出，不能跳过）
3. 反思结论有优化项 → 修改 AGENTS.md / MEMORY.md（与本次改动一起提交）
4. 反思结论无优化项 → 在 commit message 写明 `自我反思 - 本次无流程优化项`
5. **然后才能** `git merge` + `git push`

### 必答六问

每次开发完成后回答：

1. **根因** — 这次问题/改动的根本原因是什么？
2. **历史** — 是否是反复出现的同类问题？（查 MEMORY.md，反复出现是第几次？）
3. **流程** — 现有流程是否有漏洞导致这次问题？
4. **预防** — 能否通过加一条规则永久避免？
5. **浪费** — 这次有没有浪费时间的操作？（无效命令、绕弯路，必须列出具体步骤）
6. **Token** — 有没有浪费 token 的模式？（通读大文件、重复搜索，必须列出具体步骤）

**判断标准**：第 5 问（浪费）和第 6 问（Token）必须列出本次开发的具体步骤和优化动作。列不出具体步骤，说明反思不充分，需重新反思。

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

**通用前置**：先看报错信息本身，定位到文件:行号，再决定下一步。不要一上来就通读整个模块。复现优先：先稳定复现，再定位根因，再修复。改一处验证一处，不要攒一堆改动一起验证。

**类型 A：前端数据不显示/不更新类 bug**（"页面空白""数据不刷新""列表为空"）
1. 委派 Explore agent 定位代码 → 拿到数据流（store/composable/API 调用链）
2. `curl` 直测后端 API → 确认后端数据是否正常返回
3. 后端正常 → 读前端 store/composable 的响应式依赖，80% 的"不刷新"根因是依赖项缺失或响应式追踪断裂
4. 后端异常 → `mongosh` 查对应集合数据，确认是数据问题还是查询逻辑问题

**禁止**：❌ 写 Python 脚本查 MongoDB（curl API 能确认的事不走 DB 直查）；❌ 在确定根因前开浏览器自动化逐项试；❌ 写多个诊断脚本逐个跑。

**类型 B：环境/工具类问题**（命令找不到、模块导入失败、端口冲突）
- 先用一条命令确认环境状态（`where python` / `pip show <pkg>` / `netstat -ano | findstr :8000`），**不要试了才知道不行**
- Windows Git Bash 下 `grep`/`ls`/`test` 部分版本行为与 Linux 不同，确认命令可用性再批量用

**类型 C：LLM 调用失败类**（provider 报错、超时、空响应）
- 先看 `.env` 对应 provider 的 `API_KEY` 和 `*_BASE_URL` 是否配置
- 看 backend 日志（`docker-compose logs backend` 或本地日志）确认是鉴权失败、限频还是网络问题
- 注意 Tushare 低积分账号会把"频率超限(40203)"包装成"token 不对"，见 MEMORY.md 验证类 #1

**类型 D：前端一直转圈/加载不出来的性能卡顿**
- 第一步：`curl -w "%{time_total}s"` 直接测对应 API 耗时。耗时 > 5s 即后端慢，耗时 < 1s 则查前端响应式/loading 状态
- 第二步（后端慢）：看 backend 日志该请求内部触发了什么耗时操作（全市场拉取、LLM 调用、大量 DB 查询），`grep` 请求 trace_id 追踪
- **设计红线：列表/查询类接口禁止同步触发"拉全市场/全量"级外部请求**（如东方财富 5868 条快照），必须走入库缓存（market_quotes 等）或按需精确查询；兜底补字段只能针对"库中真正缺失的少数项"，不能因个别字段缺失就重新拉全量

**通用原则：能 curl / 能读代码确认的，绝不写诊断脚本。**

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

### 多对话并行开发

支持多个对话同时开发，每个对话各自 `create` 独立 worktree。隔离边界：

- **开发阶段完全隔离**：每个 worktree 有独立工作目录、分支、暂存区、HEAD，文件编辑与提交互不可见、互不影响。
- **共享只读资源无冲突**：venv、`node_modules`（junction 软链）共享只读，不构成竞争。
- **收尾阶段是共享瓶颈**：所有对话的 `finish` 都要在主工作区 `checkout main → merge → push origin main`，远程 `main` 是单一串行点。

**收尾必须错开执行**（防止 push 冲突与主工作区竞争，也是历史丢代码事故的根因，见 MEMORY.md 二.6）：

- 一次只让一个对话进入 `finish`；其他对话先在各自 worktree 内 `git commit` 改动，等前一个收尾完成再开始自己的。
- 批量收尾可改用 `python scripts/git/worktree.py finish <task> --no-push`：先只合并到本地 main（不删 worktree、不推送），攒完后串行 `git push origin main` 一次推完，再逐个跑不带 `--no-push` 的 finish 清理 worktree。
- 并发 `git push origin main` 会因 non-fast-forward 失败（脚本中断，不丢代码），失败方需 `git pull --rebase` 合并远程后重试 push。

**禁止**：一个对话去 `finish` 或 `git worktree remove` 另一个对话尚未收尾的 worktree。随时可用 `python scripts/git/worktree.py status` 查看全局在跑的 worktree，避免误判。

### 创建流程

主工作区路径固定 `D:\Github\TradingAgentsA`，worktree 统一放 `D:\Github\TradingAgentsA\.worktrees\<task-name>`。

#### 首选：脚本创建（强制）

```bash
cd D:\Github\TradingAgentsA
python scripts/git/worktree.py create <task-name>
# 脚本自动完成：建 worktree + 三重验证 + 软链 node_modules
```

#### 手动创建（仅当脚本失败时回退）

```bash
# 1. 从 main 建隔离 worktree
git worktree add .worktrees/<task-name> -b feat/<task-name> main
cd .worktrees/<task-name>

# 2. Python：worktree 共享主仓库的 venv，无需重新安装依赖
#    （直接用主仓库 .venv 的解释器，或在 worktree 内建独立 venv）

# 3. 前端：worktree 内 node_modules 较大，二选一
#    a) 软链主仓库 node_modules（Windows 用 junction，必须用绝对路径）：
#       cmd //c "mklink /J .worktrees\<task-name>\frontend\node_modules D:\Github\TradingAgentsA\frontend\node_modules"
#       ⚠️ 相对路径（..\..\frontend\node_modules）会解析到错误位置，必须用绝对路径
#    b) 或在 worktree 内单独 yarn install（耗时但隔离）

# 4. add 后必须立即三重验证（add 返回成功也可能未注册），任一失败即停止、不可继续操作
git worktree list               # 应能看到本次会话的 worktree
git -C .worktrees/<task-name> rev-parse --show-toplevel   # 应显示 .worktrees\<task-name> 路径
git -C .worktrees/<task-name> branch --show-current        # 应显示 feat/<task-name>
```

- Python 后端无需在 worktree 内重新 `pip install`（共享主仓库 venv 即可，依赖变更时在主仓库装一次）。
- 前端 `node_modules` 大，优先软链主仓库的，避免每个 worktree 都 yarn install。

### 收尾清单（merge/push 后唯一权威顺序）

> 这是 worktree 收尾的**唯一权威流程**，铁律第4条、工作流硬规则、开发流程第4步均指向此处。四步连续不可分割：**合并 → 推送 → 删 worktree → prune**。
>
> ⚠️ **禁止手敲收尾命令**（手敲易漏步骤、易误用 `-D` 强删分支导致丢代码）。收尾**必须用脚本**：`python scripts/git/worktree.py finish <task-name>`，脚本内置机械保护（见下）。仅当脚本失败且确认安全时才回退到手动流程。

#### 首选：脚本收尾（强制）

```bash
# 在主工作区执行（脚本会自动处理切换、合并、推送、删除、prune）
cd D:\Github\TradingAgentsA
python scripts/git/worktree.py finish <task-name>
```

脚本 `finish` 子命令在删除前**强制三重机械验证**，任一不满足即中止（防止丢代码）：
1. **worktree 干净**：`git status --porcelain` 无输出（有未提交改动 → 拒绝删）
2. **提交已全部进 main**：`git rev-list --count main..feat/<task>` = 0（有未合并提交 → 拒绝删）
3. **本地 main 与 origin/main 同步**：`git rev-list --count main...origin/main` 左侧 = 0（push 未成功 → 拒绝删）

脚本其他保护：
- 用 `git branch -d`（非 `-D`）删分支，git 自动拒绝删未合并分支；删除被拒即中止。
- `--no-push` 模式只合并到本地 main，**不删 worktree、不删分支**（未推送就删 = 丢代码风险）。
- 删 worktree 先非 force，失败才升级（保留 git 脏改动保护）。

脚本成功输出包含「任务 <task> 收尾完成（合并+推送+清理全部成功）」才算完成。

#### 手动收尾（仅当脚本失败时回退，必须逐步执行并核对）

1. 在 worktree 内确认所有改动已提交（`git status` 干净）
2. 切回主工作区：`cd D:\Github\TradingAgentsA`
3. `git checkout main`
4. `git merge --no-ff feat/<task-name>`（保留分支历史）
5. `git push origin main`
6. **机械验证（防丢代码，不可跳过）**：
   - `git rev-list --count main..feat/<task-name>` 应为 0（分支提交已全部进 main）
   - `git rev-list --count main...origin/main` 左侧数字应为 0（本地已推送）
   - 两条全过才继续；任一非 0 立即停止排查。
7. `git worktree remove .worktrees/<task-name>`（删 worktree 目录）
   - **删除前安全检查**：① worktree 内 `git status` 干净；② 已成功 merge 到 main；③ 已成功 push。三条全满足才 remove。
   - 若 remove 报目录被占用（Windows 文件锁）：先删 `frontend/node_modules` junction（`cmd //c "rmdir frontend\node_modules"`），确认无进程占用（dev server / python），再重试或手动删。
8. `git branch -d feat/<task-name>`（删功能分支，**禁用 `-D` 强删**；`-d` 被拒说明 git 认为未合并，必须排查）
9. `git worktree prune`（清理残留）
10. `git worktree list` 确认无残留 → 才能报告"已完成"

### 任务完成标准（全部满足才能报告完成）

- ✅ 代码已合并到 main 并 push 成功
- ✅ worktree 已删除，`git worktree list` 无残留
- ✅ 验证证据已提供（命令 + 输出，见「统一验证清单」）
- ✅ 自我反思已完成（写入 MEMORY.md 或本文件）

## 质量与提交

- 修 bug 前先定位根因，不要症状式修补（治标不治本）。
- 改动最小化：只改需要改的，不顺便重构无关代码。
- 提交前 `git fetch` + 检查是否有冲突。
- 完成判定：编译/类型检查通过 + 功能验证通过 + 无回归 + 验证证据已提供（详见「统一验证清单」与「任务完成标准」）。
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
# worktree 管理（隔离开发流程，强制使用，见「worktree 管理」章节）
python scripts/git/worktree.py create <task>   # 建隔离 worktree（三重验证+软链）
python scripts/git/worktree.py finish <task>   # 收尾（合并→推送→删worktree→prune，含机械保护）
python scripts/git/worktree.py status          # 查看所有 worktree 状态

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
- ❌ `git worktree add` 后不三重验证就开始 git 写操作（可能游离操作污染主工作区）
- ❌ **手敲 worktree 收尾命令**（必须用 `python scripts/git/worktree.py finish`，含机械保护；手敲易漏步骤/误用 `branch -D` 强删导致丢代码）
- ❌ **用 `git branch -D` 强制删未验证合并的分支**（必须 `git branch -d`，git 会拒绝删未合并分支；`-D` 绕过保护会丢代码）
- ❌ 合并推送后不删 worktree（`git worktree list` 残留）
- ❌ 没有验证证据就声称完成（"编译通过"≠"完成"）
- ❌ 服务端链路改动只跑单测不跑真实接口验证
- ❌ 用浏览器验证服务端逻辑 / 主动开浏览器自动化验证前端 UI（应 curl API + mongosh 直查；前端只跑 type-check，UI 问题等用户反馈）
- ❌ 在代码里硬编码密钥、端口、数据库连接串（应走 `.env` + Settings）
- ❌ 用 `requirements.txt` 声明依赖（已废弃，用 `pyproject.toml`）
- ❌ 前端用 npm（本项目用 yarn）
- ❌ 盲目合并上游 `TauricResearch/TradingAgents`（本项目是选择性吸收，见 `docs/maintenance/`）
- ❌ 改完 AGENTS.md 不做质量审查
- ❌ 用只读 agent 做需要写文件的任务
- ❌ 耗时操作不提前告知用户
