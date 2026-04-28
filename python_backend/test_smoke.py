"""
Backend Smoke Test — ASI 迭代标准
验证核心模块能正常导入和基础运行
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))


def test_imports():
    """所有核心模块可导入"""
    from models import Species, Agent, TopologyEdge, HistoryEntry
    from deepseek_client import call_deepseek
    from tavily_search import format_search_results
    from executor import execute_agent, execute_generation
    from evaluator import evaluate
    from evolver import mutate
    from evolution_loop import save_species, load_species
    from genesis import genesis
    from main import app
    print("✅ All imports passed")


def test_model_creation():
    """Pydantic 模型能正常创建"""
    from models import Species, Agent, TopologyEdge
    agent = Agent(
        id="a1",
        mind_model="decomposer",
        prompt_gene="拆解任务",
        tools=[],
        input_schema=["raw_goal"],
        output_schema=["sub_goals"],
        temperature_gene=0.2
    )
    assert agent.id == "a1"
    print("✅ Model creation passed")


def test_tavily_formatter():
    """Tavily 结果格式化"""
    from tavily_search import format_search_results
    mock_data = {
        "answer": "AI提升了制造业效率",
        "results": [
            {"title": "Test", "url": "https://example.com", "content": "效率提升30%"}
        ]
    }
    text = format_search_results(mock_data, max_chars=500)
    assert "效率提升30%" in text
    print("✅ Tavily formatter passed")


if __name__ == "__main__":
    test_imports()
    test_model_creation()
    test_tavily_formatter()
    print("\n🧬 ASI Smoke Test Complete")
