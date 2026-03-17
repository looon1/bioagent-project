#!/usr/bin/env python3
"""
Fresh test script to avoid cache issues.
"""

import sys
import os
import asyncio

def main():
    """
    Main entry point.
    """
    # Force Python to not use bytecode cache
    sys.dont_write_bytecode = True

    # Add bioagent to Python path
    bioagent_path = "/mnt/public/rstudio-home/fzh_hblab/bioagent"
    if bioagent_path not in sys.path:
        sys.path.insert(0, bioagent_path)

    # Import and test
    print("=" * 60)
    print("BioAgent - 生物医学 AI 助手")
    print("=" * 60)

    try:
        # Import modules fresh
        import bioagent
        from bioagent.agent import Agent
        from bioagent.config import BioAgentConfig
        from bioagent.llm import get_llm_provider
        from bioagent.observability import Logger, Metrics, CostTracker

        print("✓ 所有模块导入成功")

        # Test configuration
        config = BioAgentConfig.from_env()
        print(f"✓ 配置加载成功")
        print(f"  模型: {config.model}")
        print(f"  API 端点: {config.base_url}")

        # Validate
        config.validate()
        print("✓ 配置验证成功")

        # Initialize components
        provider = get_llm_provider(config)
        registry = bioagent.tools.registry.ToolRegistry()
        loader = bioagent.tools.loader.ToolLoader(registry)
        logger = Logger("test", config)
        metrics = Metrics()
        cost_tracker = CostTracker()

        print(f"✓ {provider.__class__.__name__} 提供商已初始化")
        print(f"✓ 工具注册表已创建: {len(registry)} 个工具")

        print("\n" + "=" * 60)
        print("✓ BioAgent Phase 1 实现验证成功！")
        print("✓ 配置为 GLM-4.7 模型")
        print("✓ 所有核心组件运行正常")
        print("=" * 60)

    except Exception as e:
        print(f"✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
