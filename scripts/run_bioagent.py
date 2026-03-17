#!/usr/bin/env python3
"""
Simple script to run BioAgent with GLM-4.7 model.
"""

import sys
import os
import asyncio

# Add bioagent to Python path
bioagent_path = "/mnt/public/rstudio-home/fzh_hblab/bioagent"
if bioagent_path not in sys.path:
    sys.path.insert(0, bioagent_path)

# Import bioagent modules normally
from bioagent.agent import Agent
from bioagent.config import BioAgentConfig


async def run_agent_query(query: str):
    """
    Run BioAgent with a query.

    Args:
        query: The user's question or task
    """
    # Load configuration from .env file
    config = BioAgentConfig.from_env()

    # Print configuration info
    print("=" * 60)
    print("BioAgent - 生物医学 AI 助手")
    print("=" * 60)
    print(f"模型: {config.model}")
    print(f"API 端点: {config.base_url}")
    print(f"日志级别: {config.log_level}")
    print("=" * 60)
    print()

    # Initialize agent
    try:
        agent = Agent(config=config)

        # Execute the query
        print(f"\n用户问题: {query}\n")
        print("Agent: 思考中...")

        response = await agent.execute(query)

        print(f"\nAgent 回答:\n{response}\n")

        # Print cost summary
        summary = agent.get_summary()
        print("\n--- 会话摘要 ---")
        print(f"LLM 调用次数: {summary['state']['llm_calls']}")
        print(f"工具调用次数: {summary['state']['tool_calls']}")
        print(f"总成本: ${summary['costs']['total_cost']:.4f}")
        print(f"总 tokens: {summary['costs']['total_tokens']}")

    except ValueError as e:
        print(f"\n错误: 配置问题 - {e}")
        print("\n请检查 .env 文件是否正确配置了 API 密钥。")
        print("必需的环境变量:")
        print("  - ANTHROPIC_API_KEY")
        print("  - BIOAGENT_BASE_URL")
        print("  - BIOAGENT_MODEL")
        sys.exit(1)

    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """Main entry point."""
    # Check if query is provided
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        asyncio.run(run_agent_query(query))
    else:
        # Interactive mode
        print("BioAgent 交互式模式")
        print("输入您的查询（输入 'quit' 退出）：")

        async def interactive_mode():
            config = BioAgentConfig.from_env()
            agent = Agent(config=config)

            while True:
                try:
                    user_input = input("\n用户: ").strip()

                    if user_input.lower() in ("quit", "exit", "q"):
                        print("\n再见！")
                        break

                    if not user_input:
                        continue

                    print(f"Agent: 处理中...")
                    response = await agent.execute(user_input)
                    print(f"Agent: {response}")

                except KeyboardInterrupt:
                    print("\n使用 Ctrl+C 退出...")
                    break

        asyncio.run(interactive_mode())


if __name__ == "__main__":
    main()
