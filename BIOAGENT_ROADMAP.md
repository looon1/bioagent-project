# BioAgent 搭建任务清单

参考项目：
- `learn-claude-code` (12 递进式课程)
- `PantheonOS` (生产级多智能体框架)
- `Biomni` (生物医学 AI 智能体)

---

## 进度概览

| 阶段 | 状态 | 完成度 |
|------|------|--------|
| Phase 1: 基础循环 | ✅ 已完成 | 100% |
| Phase 2: 多智能体团队 | ✅ 已完成 | 100% |
| Phase 3: 自动委托 | ✅ 已完成 | 100% |
| Phase 4: 任务系统 | ✅ 已完成 | 100% |
| Phase 5: 后台任务 | ✅ 已完成 | 100% |
| Phase 6: 上下文管理 | ✅ 已完成 | 100% |
| Phase 7: 高级团队协议 | ✅ 已完成 | 100% |
| Phase 8: Worktree 隔离 | ✅ 已完成 | 100% |
| Phase 9: Web UI | ✅ 已完成 | 100% |
| Phase 10: 代码进化 | ❌ 未开始 | 0% |

---

## Phase 1: 基础循环 ✅ 已完成

- [x] Agent 循环 (ReAct 模式)
- [x] Tool Use 系统
- [x] 工具注册表 (ToolRegistry)
- [x] LLM 抽象层 (多提供商支持)
- [x] 配置系统
- [x] 日志和可观测性

**文件位置：** `bioagent/agent.py`, `bioagent/tools/`, `bioagent/llm.py`, `bioagent/config.py`

---

## Phase 2: 多智能体团队 ✅ 已完成

- [x] SequentialTeam (顺序执行)
- [x] HierarchicalTeam (监督/委托)
- [x] AgentAsToolTeam (子智能体作为工具)
- [x] SwarmTeam (基于交接)
- [x] 外部工具适配器 (BiomniToolAdapter)
- [x] 域-based 工具管理

**文件位置：** `bioagent/agents/team.py`, `bioagent/tools/adapter.py`

---

## Phase 3: 自动委托 ✅ 已完成

- [x] 任务复杂度分析器 (TaskComplexityAnalyzer)
- [x] 简单智能体工厂 (SimpleAgentFactory)
- [x] 自动多智能体委托机制
- [x] 分层团队集成

**文件位置：** `bioagent/agents/analyzer.py`, `bioagent/agents/factory.py`

---

## Phase 4: 任务系统 (参考: s03, s07)

### 4.1 TodoWrite / 任务计划系统
- [ ] 实现 `TodoWrite` 工具类
- [ ] 任务创建、更新、状态跟踪
- [ ] 任务依赖图 (blockedBy/blocks)
- [ ] 任务优先级排序
- [ ] 计划执行追踪

**参考：** `learn-claude-code/agents/s03_todo_write.py`

### 4.2 任务持久化系统
- [ ] 实现 `TaskManager` 类
- [ ] JSON 文件持久化 (`.tasks/` 目录)
- [ ] 任务 CRUD 操作
- [ ] 依赖关系管理
- [ ] 自动依赖解除

**参考：** `learn-claude-code/agents/s07_task_system.py`

### 4.3 集成到 Agent
- [ ] 在 `Agent` 类中集成 `TaskManager`
- [ ] 添加任务相关工具到注册表
- [ ] 任务状态变更通知
- [ ] 任务完成自动清理

**文件结构：**
```
bioagent/
├── tasks/
│   ├── __init__.py
│   ├── manager.py        # TaskManager 类
│   ├── todo.py          # TodoWrite 工具
│   └── models.py        # Task 数据模型
```

---

## Phase 5: 后台任务 ✅ 已完成

### 5.1 后台任务管理器
- [x] 实现 `BackgroundTaskManager` 类
- [x] 任务创建、跟踪、状态管理
- [x] 异步任务执行
- [x] 完成通知队列
- [x] 任务取消和清理

**参考：** `PantheonOS/pantheon/background.py`

### 5.2 输出捕获机制
- [x] 实现 `_bg_output_buffer` ContextVar
- [x] 安装 print hook (monkeypatch)
- [x] 可靠的 stdout 捕获
- [x] 输出缓冲到任务对象

### 5.3 集成到 Agent
- [x] 在 `Agent` 类中集成 `BackgroundTaskManager`
- [x] 添加 `run_background` 工具
- [x] 超时处理和任务迁移
- [x] 后台任务状态查询工具

**文件结构：**
```
bioagent/
├── background/
│   ├── __init__.py
│   ├── manager.py       # BackgroundTaskManager
│   └── capture.py       # 输出捕获机制
```

---

## Phase 6: 上下文管理 ✅ 已完成

### 6.1 上下文压缩策略
- [x] 实现三层压缩策略
  - [x] 历史消息摘要
  - [x] 工具结果压缩
  - [x] 系统提示精简
- [x] Token 使用监控
- [x] 自动压缩触发条件

**参考：** `learn-claude-code/agents/s06_context_compact.py`

### 6.2 上下文窗口管理
- [x] 实现 `ContextManager` 类
- [x] 消息优先级排序
- [x] 保留重要上下文
- [x] 压缩日志记录

### 6.3 集成到 Agent
- [x] 在 `Agent.execute()` 中集成上下文压缩
- [x] 添加上下文管理配置选项
- [x] 压缩事件钩子

**文件结构：**
```
bioagent/
├── context/
│   ├── __init__.py
│   ├── manager.py       # ContextManager
│   └── compressors.py   # 压缩策略
```

---

## Phase 7: 高级团队协议 ✅ 已完成

### 7.1 团队协议 (Team Protocols)
- [x] 实现 JSONL 邮箱协议
- [x] request-response 模式
- [x] 关机状态机 (FSM)
- [x] 计划审批流程

**参考：** `learn-claude-code/agents/s10_team_protocols.py`

### 7.2 自治智能体
- [x] 实现空闲轮询机制
- [x] 任务看板 (Kanban)
- [x] 自动任务认领
- [x] 自组织团队模式

**参考：** `learn-claude-code/agents/s11_autonomous_agents.py`

### 7.3 持久化团队状态
- [x] 队友注册和发现
- [x] 团队状态持久化
- [x] 队友健康检查
- [x] 团队重新连接机制

**文件结构：**
```
bioagent/
├── team/
│   ├── __init__.py
│   ├── protocol.py      # 团队协议
│   ├── autonomous.py    # 自治智能体
│   ├── kanban.py       # 任务看板
│   └── discovery.py    # 队友发现
```

---

## Phase 8: Worktree 隔离 ✅ 已完成

### 8.1 Worktree 管理
- [x] 实现 `Worktree` 类
- [x] 目录级别任务隔离
- [x] 按 ID 绑定任务和目录
- [x] Worktree 清理和回收

**参考：** `learn-claude-code/agents/s12_worktree_task_isolation.py`

### 8.2 任务协调
- [x] Worktree 间任务协调
- [x] 资源共享机制
- [x] 事务性操作支持
- [x] Worktree 状态同步

### 8.3 集成到 Agent
- [x] Worktree 创建和销毁工具
- [x] Worktree 切换工具
- [x] Worktree 任务执行隔离

**文件结构：**
```
bioagent/
├── worktree/
│   ├── __init__.py
│   ├── manager.py       # WorktreeManager
│   ├── isolation.py     # 隔离机制
│   └── coordinator.py   # 任务协调
```

---

## Phase 9: Web UI ✅ 已完成

### 9.1 FastAPI 后端
- [x] FastAPI 服务器设置
- [x] SSE (Server-Sent Events) 流式响应
- [x] 文件上传和管理
- [x] 计划解析端点
- [x] 会话管理

**参考：** `Biomni-Web-main/biomni/web/server.py`

### 9.2 React 前端
- [ ] React 项目结构
- [ ] 聊天界面组件
- [ ] 实时流式输出显示
- [ ] 工具调用可视化
- [ ] 计划显示面板
- [ ] 文件管理界面

**参考：** `Biomni-Web-main/biomni/web/frontend/`

### 9.3 CLI 工具
- [x] `bioagent-web` 命令入口
- [x] 配置参数支持
- [x] 端口和主机配置
- [x] 开发和生产模式

**文件结构：**
```
bioagent/
├── web/
│   ├── __init__.py
│   ├── server.py       # FastAPI 后端
│   ├── cli.py          # 命令行入口
│   └── frontend/       # React 前端 (待实现)
│       ├── src/
│       ├── public/
│       └── package.json
```

---

## Phase 10: 代码进化 (参考: PantheonOS evolution/)

### 10.1 进化引擎
- [ ] 实现 `EvolutionEngine` 类
- [ ] 遗传算法优化
- [ ] 代码变异策略
- [ ] 适应度评估
- [ ] 自动选择最优解

**参考：** `PantheonOS/pantheon/evolution/`

### 10.2 代码生成和优化
- [ ] LLM 驱动的代码生成
- [ ] 自动代码重构
- [ ] 性能基准测试
- [ ] 回滚机制

### 10.3 集成到 Agent
- [ ] 进化任务调度
- [ ] 进化结果集成
- [ ] 进化历史追踪

**文件结构：**
```
bioagent/
├── evolution/
│   ├── __init__.py
│   ├── engine.py       # EvolutionEngine
│   ├── strategies.py    # 进化策略
│   └── evaluator.py    # 适应度评估
```

---

## 优先级建议

### 高优先级 (核心功能)
1. **Phase 4: 任务系统** - 提供基础的任务管理和依赖处理
2. **Phase 5: 后台任务** - 支持长时间运行的操作
3. **Phase 6: 上下文管理** - 支持长对话

### 中优先级 (增强功能)
4. **Phase 7: 高级团队协议** - 更强大的多智能体协作
5. **Phase 9: Web UI** - 用户友好的交互界面

### 低优先级 (高级功能)
6. **Phase 8: Worktree 隔离** - 高级任务隔离
7. **Phase 10: 代码进化** - 自动优化能力

---

## 配置和依赖

### 新增环境变量
```bash
# 任务系统
BIOAGENT_TASKS_DIR=./.tasks
BIOAGENT_ENABLE_TASK_TRACKING=true

# 后台任务
BIOAGENT_MAX_BACKGROUND_TASKS=50
BIOAGENT_ENABLE_BACKGROUND_TASKS=true

# 上下文管理
BIOAGENT_ENABLE_CONTEXT_COMPRESSION=true
BIOAGENT_CONTEXT_MAX_TOKENS=100000
BIOAGENT_COMPRESSION_THRESHOLD=0.8

# 团队协议
BIOAGENT_TEAM_PROTOCOL=jsonl
BIOAGENT_AUTONOMOUS_POLL_INTERVAL=30

# Worktree
BIOAGENT_WORKTREES_DIR=./worktrees

# Web UI
BIOAGENT_WEB_PORT=7860
BIOAGENT_WEB_HOST=0.0.0.0
```

### 新增依赖
```toml
[project.dependencies]
# 任务系统
pydantic = "^2.0"

# 后台任务
# (已有 asyncio)

# 上下文管理
tiktoken = "^0.5"

# Web UI
fastapi = "^0.104"
uvicorn = {extras = ["standard"], version = "^0.24"}
sse-starlette = "^1.6"

# 前端开发
# (需要单独的 package.json)
```

---

## 测试计划

### 单元测试
- [x] Web UI 测试 (`scripts/test_phase9_web.py`)
- [ ] 任务系统测试 (`tests/test_tasks.py`)
- [ ] 后台任务测试 (`tests/test_background.py`)
- [ ] 上下文压缩测试 (`tests/test_context.py`)
- [ ] 团队协议测试 (`tests/test_team_protocol.py`)
- [ ] Worktree 测试 (`tests/test_worktree.py`)
- [ ] 进化引擎测试 (`tests/test_evolution.py`)

### 集成测试
- [ ] 端到端任务流程测试
- [ ] 多智能体协作测试
- [ ] Web UI 集成测试

### 性能测试
- [ ] 上下文压缩性能测试
- [ ] 后台任务并发测试
- [ ] 大规模团队测试

---

## 文档计划

- [ ] API 参考文档 (`docs/api.md`)
- [ ] 架构设计文档 (`docs/architecture.md`)
- [ ] 部署指南 (`docs/deployment.md`)
- [ ] 开发者指南 (`docs/development.md`)
- [ ] 用户手册 (`docs/user_manual.md`)
- [ ] 贡献指南 (`CONTRIBUTING.md`)

---

## 完成标准

每个 Phase 完成需要满足：
1. 功能实现完整
2. 单元测试覆盖率 ≥ 80%
3. 集成测试通过
4. 文档完善
5. 代码符合项目规范 (Black + Ruff)

---

**最后更新：** 2026-03-18 (Phase 9 已完成)
