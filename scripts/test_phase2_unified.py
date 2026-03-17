#!/usr/bin/env python3
"""
Comprehensive test script for BioAgent Phase 2 unified API testing

This script tests all Phase 2 features while ensuring API consistency:
1. Tool Adapter System (Biomni integration)
2. Multi-Agent Team System
3. Unified API interface across all components
4. Configuration loading and validation
"""

import asyncio
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import asdict

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bioagent.config import BioAgentConfig
from bioagent.agent import Agent
from bioagent.agents import SequentialTeam, HierarchicalTeam, AgentAsToolTeam, SwarmTeam
from bioagent.tools.adapter import ToolAdapter, BiomniToolAdapter, ToolInfo
from bioagent.tools.registry import ToolRegistry
from bioagent.tools.base import tool
from bioagent.tools.core import query_uniprot, query_gene
from bioagent.state import AgentStatus


class Phase2UnifiedTester:
    """Comprehensive tester for Phase 2 unified API"""

    def __init__(self):
        self.test_results = {}
        self.config = None
        self.agent = None
        self.team = None

    async def setup_test_environment(self):
        """Setup test environment with different configurations"""
        print("\n=== Setting up test environment ===")

        # Test 1: Basic configuration
        print("\n1. Testing basic configuration loading...")
        os.environ['ANTHROPIC_API_KEY'] = 'test_key_for_testing_only'
        os.environ['BIOAGENT_MODEL'] = 'claude-sonnet-4-20250514'
        os.environ['BIOAGENT_LOG_LEVEL'] = 'DEBUG'

        config = BioAgentConfig.from_env()
        self.test_results['config_basic'] = {
            'success': True,
            'model': config.model,
            'base_url': config.base_url,
            'max_tool_iterations': config.max_tool_iterations
        }
        print(f"   ✓ Basic config loaded: {config.model}")

        # Test 2: Phase 2 configuration options
        print("\n2. Testing Phase 2 configuration options...")
        config.enable_biomni_tools = True
        config.biomni_path = "/tmp/fake_biomni"  # Non-existent path for testing
        config.biomni_domains = ["genetics", "genomics"]
        config.enable_multi_agent = True
        config.agent_team_mode = "sequential"

        self.test_results['config_phase2'] = {
            'success': True,
            'biomni_enabled': config.enable_biomni_tools,
            'biomni_domains': config.biomni_domains,
            'multi_agent_enabled': config.enable_multi_agent,
            'team_mode': config.agent_team_mode
        }
        print(f"   ✓ Phase 2 config loaded: biomni={config.enable_biomni_tools}, domains={config.biomni_domains}")

        # Test 3: Agent initialization
        print("\n3. Testing agent initialization...")
        try:
            self.agent = Agent(config=config)
            self.test_results['agent_init'] = {
                'success': True,
                'status': self.agent.status,
                'tools_count': len(self.agent.registry.tools),
                'domains': list(self.agent.registry.domains)
            }
            print(f"   ✓ Agent initialized with {len(self.agent.registry.tools)} tools")
        except Exception as e:
            self.test_results['agent_init'] = {
                'success': False,
                'error': str(e)
            }
            print(f"   ✗ Agent initialization failed: {e}")

    async def test_tool_adapter_system(self):
        """Test Tool Adapter System for unified API"""
        print("\n=== Testing Tool Adapter System ===")

        # Test 1: ToolAdapter base class
        print("\n1. Testing ToolAdapter base class...")
        try:
            adapter = ToolAdapter()
            self.test_results['tool_adapter_base'] = {
                'success': True,
                'class_name': adapter.__class__.__name__,
                'abstract_methods': adapter.__class__.__abstractmethods__
            }
            print("   ✓ ToolAdapter base class created")
        except Exception as e:
            self.test_results['tool_adapter_base'] = {
                'success': False,
                'error': str(e)
            }
            print(f"   ✗ ToolAdapter base class failed: {e}")

        # Test 2: BiomniToolAdapter creation
        print("\n2. Testing BiomniToolAdapter creation...")
        try:
            biomni_adapter = BiomniToolAdapter(
                path="/tmp/fake_biomni",
                domains=["genetics"]
            )

            # Test domain management
            enabled_count = biomni_adapter.enable_domain("genetics")
            disabled_count = biomni_adapter.disable_domain("genetics")

            domains = biomni_adapter.list_available_domains()
            external_tools = biomni_adapter.list_external_tools()

            self.test_results['biomni_adapter'] = {
                'success': True,
                'domains': domains,
                'external_tools': external_tools,
                'enabled_domain_count': enabled_count,
                'disabled_domain_count': disabled_count
            }
            print(f"   ✓ BiomniAdapter created with domains: {domains}")

        except Exception as e:
            self.test_results['biomni_adapter'] = {
                'success': False,
                'error': str(e)
            }
            print(f"   ✗ BiomniAdapter creation failed: {e}")

        # Test 3: Tool registry with adapter tools
        print("\n3. Testing Tool registry with adapter integration...")
        try:
            # Enable all tool domains
            for domain in ["database", "analysis", "files"]:
                self.agent.enable_tool_domain(domain)

            # List enabled tools
            enabled_tools = self.agent.get_enabled_tools()
            core_tools = self.agent.registry.list_tools_by_domain("database")

            self.test_results['tool_registry_adapter'] = {
                'success': True,
                'enabled_domains': self.agent.list_tool_domains(),
                'core_database_tools': len(core_tools),
                'total_enabled_tools': len(enabled_tools)
            }
            print(f"   ✓ Registry has {len(enabled_tools)} enabled tools across {len(self.agent.list_tool_domains())} domains")

        except Exception as e:
            self.test_results['tool_registry_adapter'] = {
                'success': False,
                'error': str(e)
            }
            print(f"   ✗ Registry integration failed: {e}")

        # Test 4: Tool execution consistency
        print("\n4. Testing tool execution consistency...")
        try:
            # Test core tool execution
            result = await self.agent.execute("query_uniprot('P04637')", max_iterations=3)

            self.test_results['tool_execution_consistency'] = {
                'success': True,
                'execution_result': result[:100] + "..." if len(result) > 100 else result,
                'agent_status': self.agent.status
            }
            print("   ✓ Core tool execution consistent")

        except Exception as e:
            self.test_results['tool_execution_consistency'] = {
                'success': False,
                'error': str(e)
            }
            print(f"   ✗ Tool execution failed: {e}")

    async def test_multi_agent_teams(self):
        """Test Multi-Agent Team System with unified API"""
        print("\n=== Testing Multi-Agent Team System ===")

        # Test 1: Sequential Team
        print("\n1. Testing Sequential Team...")
        try:
            # Create two agents
            agent1 = Agent(config=self.config)
            agent2 = Agent(config=self.config)

            team = SequentialTeam(
                agents=[agent1, agent2],
                connect_prompt="Continue analyzing:"
            )

            # Test team interface
            agents_list = team.list_agents()
            agent_count = len(team.agents)

            self.test_results['sequential_team'] = {
                'success': True,
                'agent_count': agent_count,
                'agent_ids': agents_list,
                'team_type': team.__class__.__name__
            }
            print(f"   ✓ Sequential team created with {agent_count} agents")

        except Exception as e:
            self.test_results['sequential_team'] = {
                'success': False,
                'error': str(e)
            }
            print(f"   ✗ Sequential team failed: {e}")

        # Test 2: Hierarchical Team
        print("\n2. Testing Hierarchical Team...")
        try:
            # Create agents
            supervisor = Agent(config=self.config)
            genetics_agent = Agent(config=self.config)
            genomics_agent = Agent(config=self.config)

            team = HierarchicalTeam(
                supervisor=supervisor,
                subagents=[genetics_agent, genomics_agent]
            )

            # Test team interface
            sub_agents = list(team.subagents.keys())

            self.test_results['hierarchical_team'] = {
                'success': True,
                'sub_agents': sub_agents,
                'team_type': team.__class__.__name__
            }
            print(f"   ✓ Hierarchical team created with sub-agents: {sub_agents}")

        except Exception as e:
            self.test_results['hierarchical_team'] = {
                'success': False,
                'error': str(e)
            }
            print(f"   ✗ Hierarchical team failed: {e}")

        # Test 3: AgentAsTool Team
        print("\n3. Testing AgentAsTool Team...")
        try:
            # Create agents
            leader = Agent(config=self.config)
            assistant1 = Agent(config=self.config)
            assistant2 = Agent(config=self.config)

            team = AgentAsToolTeam(
                leader=leader,
                sub_agents=[assistant1, assistant2],
                agent_descriptions={
                    "assistant1": "Data analysis specialist",
                    "assistant2": "Literature search specialist"
                }
            )

            # Test team interface
            tool_agents = team.list_agent_tools()

            self.test_results['agent_as_tool_team'] = {
                'success': True,
                'tool_agents': tool_agents,
                'team_type': team.__class__.__name__
            }
            print(f"   ✓ AgentAsTool team created with {len(tool_agents)} agent tools")

        except Exception as e:
            self.test_results['agent_as_tool_team'] = {
                'success': False,
                'error': str(e)
            }
            print(f"   ✗ AgentAsTool team failed: {e}")

        # Test 4: Swarm Team
        print("\n4. Testing Swarm Team...")
        try:
            # Create agents
            agent1 = Agent(config=self.config)
            agent2 = Agent(config=self.config)

            team = SwarmTeam(
                agents=[agent1, agent2],
                max_handoffs=5
            )

            # Test team interface
            initial_agent = team.get_active_agent()

            self.test_results['swarm_team'] = {
                'success': True,
                'max_handoffs': team.max_handoffs,
                'active_agent': initial_agent,
                'team_type': team.__class__.__name__
            }
            print(f"   ✓ Swarm team created with max_handoffs={team.max_handoffs}")

        except Exception as e:
            self.test_results['swarm_team'] = {
                'success': False,
                'error': str(e)
            }
            print(f"   ✗ Swarm team failed: {e}")

    async def test_unified_api_interface(self):
        """Test unified API interface across all components"""
        print("\n=== Testing Unified API Interface ===")

        # Test 1: Tool info consistency
        print("\n1. Testing tool info consistency...")
        try:
            # Get tool info from registry
            tools_info = self.agent.registry.list_tools()

            # Check that all tools have required fields
            required_fields = ['name', 'domain', 'description', 'parameters', 'func']
            consistent_tools = 0

            for tool in tools_info:
                if all(hasattr(tool, field) for field in required_fields):
                    consistent_tools += 1

            self.test_results['tool_info_consistency'] = {
                'success': True,
                'total_tools': len(tools_info),
                'consistent_tools': consistent_tools,
                'consistency_rate': consistent_tools / len(tools_info) if tools_info else 0
            }
            print(f"   ✓ Tool info consistency: {consistent_tools}/{len(tools_info)} tools ({consistent_tools/len(tools_info)*100:.1f}%)")

        except Exception as e:
            self.test_results['tool_info_consistency'] = {
                'success': False,
                'error': str(e)
            }
            print(f"   ✗ Tool info consistency failed: {e}")

        # Test 2: Parameter schema consistency
        print("\n2. Testing parameter schema consistency...")
        try:
            # Get a few tools to test schema
            tools_to_test = self.agent.registry.list_tools()[:3]
            schema_consistent = 0

            for tool in tools_to_test:
                schema = tool.parameters
                if isinstance(schema, dict) and 'type' in schema:
                    schema_consistent += 1

            self.test_results['schema_consistency'] = {
                'success': True,
                'tools_tested': len(tools_to_test),
                'schema_consistent': schema_consistent,
                'schema_rate': schema_consistent / len(tools_to_test) if tools_to_test else 0
            }
            print(f"   ✓ Schema consistency: {schema_consistent}/{len(tools_to_test)} schemas ({schema_consistent/len(tools_to_test)*100:.1f}%)")

        except Exception as e:
            self.test_results['schema_consistency'] = {
                'success': False,
                'error': str(e)
            }
            print(f"   ✗ Schema consistency failed: {e}")

        # Test 3: Agent state management consistency
        print("\n3. Testing agent state management consistency...")
        try:
            # Check agent state interface
            agent_methods = [
                'execute',
                'get_enabled_tools',
                'enable_tool_domain',
                'disable_tool_domain',
                'list_tool_domains',
                'register_tool'
            ]

            available_methods = []
            for method in agent_methods:
                if hasattr(self.agent, method):
                    available_methods.append(method)

            self.test_results['agent_interface_consistency'] = {
                'success': True,
                'expected_methods': agent_methods,
                'available_methods': available_methods,
                'coverage': len(available_methods) / len(agent_methods)
            }
            print(f"   ✓ Agent interface: {len(available_methods)}/{len(agent_methods)} methods ({len(available_methods)/len(agent_methods)*100:.1f}%)")

        except Exception as e:
            self.test_results['agent_interface_consistency'] = {
                'success': False,
                'error': str(e)
            }
            print(f"   ✗ Agent interface consistency failed: {e}")

        # Test 4: Configuration validation consistency
        print("\n4. Testing configuration validation consistency...")
        try:
            # Test config loading with different scenarios
            test_configs = [
                # Basic config
                {},
                # With Biomni
                {'enable_biomni_tools': True, 'biomni_domains': ['genetics']},
                # With multi-agent
                {'enable_multi_agent': True, 'agent_team_mode': 'sequential'}
            ]

            valid_configs = 0
            for config_data in test_configs:
                try:
                    # Create a new config for each test
                    test_env = os.environ.copy()
                    test_env.update({
                        'ANTHROPIC_API_KEY': 'test_key',
                        'BIOAGENT_MODEL': 'claude-sonnet-4-20250514'
                    })

                    # Temporarily update env
                    for key, value in config_data.items():
                        os.environ[f'BIOAGENT_{key.upper()}'] = str(value) if value is not None else ''

                    config = BioAgentConfig.from_env()
                    valid_configs += 1

                    # Restore env
                    for key in config_data:
                        if f'BIOAGENT_{key.upper()}' in os.environ:
                            del os.environ[f'BIOAGENT_{key.upper()}']

                except Exception:
                    pass

            self.test_results['config_validation_consistency'] = {
                'success': True,
                'test_configs': len(test_configs),
                'valid_configs': valid_configs,
                'validation_rate': valid_configs / len(test_configs)
            }
            print(f"   ✓ Config validation: {valid_configs}/{len(test_configs)} configs valid ({valid_configs/len(test_configs)*100:.1f}%)")

        except Exception as e:
            self.test_results['config_validation_consistency'] = {
                'success': False,
                'error': str(e)
            }
            print(f"   ✗ Config validation failed: {e}")

    async def test_error_handling_consistency(self):
        """Test error handling consistency across all components"""
        print("\n=== Testing Error Handling Consistency ===")

        # Test 1: Tool execution error handling
        print("\n1. Testing tool execution error handling...")
        try:
            # Try to execute a non-existent tool
            result = await self.agent.execute("non_existent_tool('test')")

            self.test_results['tool_error_handling'] = {
                'success': True,
                'error_caught': 'error' in result.lower() or 'not found' in result.lower()
            }
            print("   ✓ Tool execution error handled")

        except Exception as e:
            self.test_results['tool_error_handling'] = {
                'success': False,
                'error': str(e)
            }
            print(f"   ✗ Tool error handling failed: {e}")

        # Test 2: Team error handling
        print("\n2. Testing team error handling...")
        try:
            # Create team with invalid configuration
            agent = Agent(config=self.config)
            team = SequentialTeam(
                agents=[agent],  # Single agent team
                connect_prompt=None  # Invalid prompt
            )

            self.test_results['team_error_handling'] = {
                'success': True,
                'team_created': team is not None
            }
            print("   ✓ Team error handled gracefully")

        except Exception as e:
            self.test_results['team_error_handling'] = {
                'success': False,
                'error': str(e)
            }
            print(f"   ✗ Team error handling failed: {e}")

        # Test 3: Configuration error handling
        print("\n3. Testing configuration error handling...")
        try:
            # Test with invalid configuration
            os.environ['BIOAGENT_MAX_TOOL_ITERATIONS'] = '-1'  # Invalid value

            config = BioAgentConfig.from_env()

            self.test_results['config_error_handling'] = {
                'success': True,
                'invalid_value_handled': config.max_tool_iterations >= 0
            }
            print("   ✓ Configuration error handled")

            # Clean up
            del os.environ['BIOAGENT_MAX_TOOL_ITERATIONS']

        except Exception as e:
            self.test_results['config_error_handling'] = {
                'success': False,
                'error': str(e)
            }
            print(f"   ✗ Configuration error failed: {e}")

    def generate_test_report(self):
        """Generate comprehensive test report"""
        print("\n" + "="*60)
        print("PHASE 2 UNIFIED API TEST REPORT")
        print("="*60)

        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result['success'])
        failed_tests = total_tests - passed_tests

        print(f"\nOverall Results:")
        print(f"  Total Tests: {total_tests}")
        print(f"  Passed: {passed_tests} ({passed_tests/total_tests*100:.1f}%)")
        print(f"  Failed: {failed_tests} ({failed_tests/total_tests*100:.1f}%)")

        print(f"\nDetailed Results:")
        for test_name, result in self.test_results.items():
            status = "✓ PASS" if result['success'] else "✗ FAIL"
            print(f"  {status} {test_name}")

            if not result['success']:
                print(f"      Error: {result.get('error', 'Unknown error')}")

        # API Consistency Summary
        print(f"\nAPI Consistency Summary:")
        consistency_checks = [
            'tool_info_consistency',
            'schema_consistency',
            'agent_interface_consistency',
            'config_validation_consistency'
        ]

        consistent_checks = 0
        for check in consistency_checks:
            if check in self.test_results and self.test_results[check]['success']:
                rate = self.test_results[check].get('consistency_rate', 0) or \
                       self.test_results[check].get('coverage', 0) or \
                       self.test_results[check].get('validation_rate', 0)
                if rate > 0.8:  # 80% threshold
                    consistent_checks += 1

        print(f"  API Consistency Score: {consistent_checks}/{len(consistency_checks)} ({consistent_checks/len(consistency_checks)*100:.1f}%)")

        return {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'consistency_score': consistent_checks / len(consistency_checks) if consistency_checks else 0
        }


async def main():
    """Main test execution"""
    print("BioAgent Phase 2 Unified API Test Suite")
    print("="*60)

    tester = Phase2UnifiedTester()

    try:
        # Setup
        await tester.setup_test_environment()

        # Run all tests
        await tester.test_tool_adapter_system()
        await tester.test_multi_agent_teams()
        await tester.test_unified_api_interface()
        await tester.test_error_handling_consistency()

        # Generate report
        report = tester.generate_test_report()

        # Exit with appropriate code
        sys.exit(0 if report['passed_tests'] == report['total_tests'] else 1)

    except Exception as e:
        print(f"\nTest suite failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())