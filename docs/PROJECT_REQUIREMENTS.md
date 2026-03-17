# BioAgent 项目需求文档

## 原始需求

构建一个生物医学领域 agent，要求如下：

1. **依据现有的 agent 构建**：参考以下项目
   - PantheonOS: https://github.com/aristoteleo/PantheonOS
   - Biomni: https://github.com/snap-stanford/Biomni
   - learn-claude-code: https://github.com/shareAI-lab/learn-claude-code/
   - 本地仓库路径：
     - PantheonOS: `/mnt/public/rstudio-home/fzh_hblab/PantheonOS`
     - Biomni-Web-main: `/mnt/public/rstudio-home/fzh_hblab/Biomni-Web-main`
     - learn-claude-code: `/mnt/public/rstudio-home/fzh_hblab/learn-claude-code`

2. **避免过度工程化**：但是需要学习 PantheonOS 搭建多智能体处理

3. **先从极简起步**：运行成本低的同时出错还容易排查

4. **选择对的模型**：支持多种模型选择，根据任务选择合适的模型

5. **拥抱模块化**：把 prompt 和 tool 剥离开，为明天的技术迭代预留热拔插接口

6. **碰到瓶颈时先加 skills**：优先通过扩展技能来增强功能，而不是修改核心代码

7. **保障可观测性**：完善的日志、指标和成本追踪系统

---

## 当前符合度状态

| 需求 | 状态 | 完成度 | 说明 |
|------|------|--------|------|
| 1. 依据 PantheonOS/Biomni 构建 | ⚠️ 部分 | 65% | 参考了架构，工具调用已修复，多智能体和 JSON 工具描述未实现 |
| 2. 避免过度工程化 | ✅ 符合 | 100% | 保持极简，核心代码量适中 |
| 3. 学习 PantheonOS 多智能体 | ❌ 未开始 | 0% | 仍是单智能体设计 |
| 4. 极简起步 | ✅ 符合 | 100% | Minimal Viable Agent 已完成，工具可正常执行 |
| 5. 低运行成本 | ✅ 符合 | 100% | 支持多种模型选择 |
| 6. 易排查错误 | ✅ 符合 | 100% | 完善的日志系统 |
| 7. 模块化：prompt/tool 分离 | ⚠️ 部分 | 70% | 物理分离了，但热拔插接口未完成 |
| 8. 热拔插接口 | ❌ 未完成 | 20% | JSON 描述是 stub，未真正实现 |
| 9. 遇到瓶颈先加 skills | ❌ 未实现 | 0% | 没有技能扩展机制 |
| 10. 可观测性 | ✅ 符合 | 100% | 日志、指标、成本追踪完整 |

---

## Skills 扩展系统设计

参考 learn-claude-code 的技能系统设计，实现两层技能注入机制：

### 目录结构

```
bioagent/
  skills/
    uniprot/
      SKILL.md
    gene-analysis/
      SKILL.md
    pubmed/
      SKILL.md
```

### SKILL.md 格式

```markdown
---
name: uniprot
description: Query UniProt database for protein information. Use when searching for protein data, sequences, or functions.
tags: database, protein, biomedical
---

# UniProt Query Skill

You now have expertise in querying the UniProt database...

## Search by Protein ID
...

## Search by Keyword
...
```

### SkillLoader 类

```python
class SkillLoader:
    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self.skills = {}
        self._load_all()

    def _load_all(self):
        """Scan all SKILL.md files and parse frontmatter."""
        for f in self.skills_dir.rglob("SKILL.md"):
            text = f.read_text()
            meta, body = self._parse_frontmatter(text)
            name = meta.get("name", f.parent.name)
            self.skills[name] = {"meta": meta, "body": body}

    def get_descriptions(self) -> str:
        """Layer 1: skill names + descriptions for system prompt."""
        ...

    def get_content(self, name: str) -> str:
        """Layer 2: full skill body returned via tool."""
        ...
```

### load_skill 工具

```python
@tool(domain="skills")
async def load_skill(skill_name: str) -> str:
    """Load and return the full content of a skill."""
    return agent.skill_loader.get_content(skill_name)
```

### 系统提示词模板

```markdown
You are BioAgent, a biomedical AI assistant.

## Available Skills
{skill_descriptions}

When you need detailed instructions for a skill, call load_skill(skill_name).
```

---

## 修复记录

### 2026-03-17: 工具调用失败问题修复

**问题描述**：所有工具调用都失败，日志显示 "Tool failed"

**根本原因**：
1. `ToolRegistry.execute()` 是同步方法，但所有工具函数都是 async，导致返回协程对象而非执行结果
2. `OpenAIProvider` 在解析工具调用时，没有将 OpenAI API 返回的 JSON 字符串参数解析为字典

**修复内容**：
1. `bioagent/tools/registry.py`:
   - 添加 `import inspect`
   - 将 `execute()` 改为 `async def execute()`
   - 使用 `inspect.iscoroutinefunction()` 检测异步工具
   - 异步工具使用 `await func(**args)`，同步工具直接调用

2. `bioagent/agent.py`:
   - 在工具调用处添加 `await`（第 196 行）

3. `bioagent/llm.py`:
   - 添加 `import json`
   - 在 `OpenAIProvider.call()` 中解析 `tc.function.arguments` 的 JSON 字符串

**验证结果**：
- ✅ 工具可以正常执行
- ✅ 日志显示 "Tool executed" 而非 "Tool failed"
- ✅ 用户查询能得到正确的生物医学信息
- ✅ 6 个工具全部注册成功（query_uniprot, query_gene, query_pubmed, run_python_code, read_file, write_file）

---

## 待实现的优先级

### P0 - 立即修复
- [x] 修复工具调用失败问题（异步执行） - 已于 2026-03-17 完成
  - 修复 `bioagent/tools/registry.py`: 将 `execute` 改为 async 方法
  - 修复 `bioagent/agent.py`: 添加 await 调用工具执行
  - 修复 `bioagent/llm.py`: 解析 OpenAI API 返回的 JSON 字符串参数

### P1 - 高优先级（符合原始需求）
- [ ] 实现完整的 JSON 工具描述系统（热拔插接口）
- [ ] 参考 PantheonOS 实现多智能体框架
- [ ] 设计并实现 skills 扩展机制
  - 参考 learn-claude-code 的两层注入机制：
    - `bioagent/skills/<name>/SKILL.md` 格式（YAML frontmatter）
    - `SkillLoader` 类扫描和加载技能
    - `load_skill()` 工具按需注入完整技能体

### P2 - 中优先级
- [ ] 从 Biomni 迁移更多生物医学工具
- [ ] 优化模型选择逻辑
- [ ] 增强可观测性 Dashboard

---

## 设计原则

在所有开发过程中，必须遵循：

1. **极简优先**：避免过度工程化，功能够用即可
2. **可观测性**：所有操作必须有日志和指标
3. **模块化**：prompt、tool、skills 分离，支持热拔插
4. **渐进增强**：从 MVP 开始，逐步添加功能
5. **先 skills 后核心**：遇到瓶颈时优先通过扩展技能解决

---

## 参考项目学习要点

### PantheonOS (多智能体模式)
- Agent 组合和层次化设计
- 基于团队的执行模式
- Agent 通信协议
- 状态管理和协调机制

### Biomni (工具管理)
- 工具描述格式和元数据
- 动态工具加载机制
- 工具验证和错误处理
- 生物医学工具集成

### learn-claude-code (Claude Code 最佳实践)
- Agent 技能系统设计（YAML frontmatter + 两层注入机制）
  - Layer 1: 技能名称和描述（约 100 tokens/skill）在系统提示词中
  - Layer 2: 完整技能体通过 load_skill() 工具按需加载
- 热拔插工具接口
- Agent 团队和子代理模式
- 可观测性最佳实践
- 模块化架构设计模式

**参考文件**：
- `agents/s05_skill_loading.py` - 技能加载实现
- `agents/s09_agent_teams.py` - Agent 团队模式
- `skills/*/SKILL.md` - 技能格式（YAML frontmatter）

---
