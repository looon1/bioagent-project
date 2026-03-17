# BioAgent 快速入门指南

## 已配置的 API

您的 API 配置已经设置在 `.env` 文件中：

- **Base URL**: `https://open.bigmodel.cn/api/coding/paas/v4`
- **API Key**: `a0412f4ae9de4b7b8cef2403f3f7f506.abcOoGU4eofGiaAk`
- **Model**: `gpt-4`

## 安装依赖

```bash
cd /mnt/public/rstudio-home/fzh_hblab

# 安装 BioAgent 包及其依赖
pip install -e .
```

## 使用方式

### 1. 命令行模式

```bash
# 单次查询
python -m bioagent.cli "查询 TP53 基因的功能"

# 交互式模式
python -m bioagent.cli -i
```

### 2. Python API

```python
import asyncio
from bioagent.agent import Agent
from bioagent.config import BioAgentConfig

async def main():
    # 加载配置（会自动读取 .env 文件）
    config = BioAgentConfig.from_env()

    # 初始化 Agent
    agent = Agent(config=config)

    # 执行查询
    response = await agent.execute(
        "查询 UniProt 数据库中胰岛素蛋白的信息"
    )

    print(response)

    # 获取会话摘要
    summary = agent.get_summary()
    print(f"总成本: ${summary['costs']['total_cost']:.4f}")

asyncio.run(main())
```

## 可用工具

### 数据库工具
- `query_uniprot`: 查询 UniProt 蛋白质数据库
- `query_gene`: 查询基因信息（通过 Gene Ontology）
- `query_pubmed`: 搜索 PubMed 文献

### 分析工具
- `run_python_code`: 安全执行 Python 代码

### 文件工具
- `read_file`: 读取文件
- `write_file`: 写入文件

## 配置选项

您可以通过修改 `.env` 文件来调整配置：

```bash
# 模型设置
BIOAGENT_MODEL=gpt-4          # 模型名称
BIOAGENT_BASE_URL=https://open.bigmodel.cn/api/coding/paas/v4  # API 端点

# API 密钥
ANTHROPIC_API_KEY=a0412f4ae9de4b7b8cef2403f3f7f506.abcOoGU4eofGiaAk

# 路径设置
BIOAGENT_DATA_PATH=./bioagent_data
BIOAGENT_LOGS_PATH=./bioagent_logs

# 日志级别
BIOAGENT_LOG_LEVEL=INFO    # 或 DEBUG 获取详细日志

# 工具迭代限制
BIOAGENT_MAX_TOOL_ITERATIONS=10
```

## 交互式命令

在交互式模式下，您可以使用以下命令：

- `quit`, `exit`, `q` - 退出程序
- `summary` - 显示会话摘要
- `reset` - 重置 Agent 状态
- `help` - 显示帮助信息

## 示例查询

### 查询蛋白信息
```
查询 UniProt 中 P01308（人胰岛素）的信息
```

### 基因分析
```
分析 TP53 基因的功能和相关信息
```

### 文献搜索
```
搜索关于 CRISPR 基因编辑的最近文献
```

### 数据分析
```
使用 Python 分析这组基因表达数据：[数据]
```

## 架构说明

BioAgent 使用 ReAct（推理+行动）模式：

1. **推理**: LLM 分析查询并决定需要执行的步骤
2. **行动**: 执行工具获取信息
3. **观察**: 将工具结果添加到上下文
4. **循环**: 继续推理直到完成查询

## 故障排查

### API 连接问题
如果遇到 API 连接错误：

```bash
# 检查 .env 文件是否正确加载
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print('BASE_URL:', os.getenv('BIOAGENT_BASE_URL'))"

# 检查网络连接
curl -I https://open.bigmodel.cn/api/coding/paas/v4
```

### 工具执行问题
如果工具执行失败：

1. 检查日志文件：`bioagent_logs/`
2. 启用调试日志：在 `.env` 中设置 `BIOAGENT_LOG_LEVEL=DEBUG`

## 下一步

Phase 1 已完成。计划中的下一阶段：

- **Phase 2**: 模块化工具系统（JSON 工具描述，动态加载）
- **Phase 3**: 多智能体系统（SequentialTeam, HierarchicalTeam）
- **Phase 4**: 知识库系统（Claude Skills 集成）
- **Phase 5**: 可观测性基础设施（Web Dashboard，SSE 流式输出）

## 支持

如需帮助或报告问题，请参考：
- 实施文档：`IMPLEMENTATION_SUMMARY.md`
- 测试脚本：`test_bioagent.py`
- 主文档：`README.md`
