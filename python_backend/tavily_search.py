"""
Tavily 搜索集成 —— 给 retriever agent 提供真实互联网搜索能力
"""
import os
import aiohttp
from typing import Optional

TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
TAVILY_API_URL = "https://api.tavily.com/search"


async def tavily_search(
    query: str,
    search_depth: str = "basic",  # basic 或 advanced
    max_results: int = 5,
    include_answer: bool = True,
    include_raw_content: bool = False
) -> dict:
    """
    调用 Tavily API 进行互联网搜索
    
    Args:
        query: 搜索查询词
        search_depth: basic(快) 或 advanced(慢但深)
        max_results: 返回结果数量
        include_answer: 是否包含 AI 生成的摘要答案
        include_raw_content: 是否包含网页原始内容
    
    Returns:
        Tavily API 的原始响应 dict
    """
    if not TAVILY_API_KEY:
        raise ValueError("TAVILY_API_KEY not set in environment")
    
    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "search_depth": search_depth,
        "max_results": max_results,
        "include_answer": include_answer,
        "include_raw_content": include_raw_content,
        "include_images": False
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(TAVILY_API_URL, json=payload) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"Tavily API error {resp.status}: {text}")
            
            data = await resp.json()
            return data


def format_search_results(data: dict, max_chars: int = 4000) -> str:
    """
    将 Tavily 搜索结果格式化为文本，供 LLM 使用
    
    返回格式：
    [搜索结果摘要]
    1. [标题] (URL)
       摘要: ...
       [原始内容片段]
    
    2. [标题] (URL)
       ...
    """
    parts = []
    
    # Tavily AI 生成的摘要答案
    answer = data.get("answer", "")
    if answer:
        parts.append(f"[搜索摘要]\n{answer}\n")
    
    # 搜索结果列表
    results = data.get("results", [])
    if results:
        parts.append("[搜索结果详情]")
        for i, r in enumerate(results, 1):
            title = r.get("title", "无标题")
            url = r.get("url", "")
            content = r.get("content", "")
            raw_content = r.get("raw_content", "")
            
            parts.append(f"\n{i}. [{title}]")
            if url:
                parts.append(f"   URL: {url}")
            if content:
                parts.append(f"   摘要: {content}")
            if raw_content:
                # 截断原始内容，避免过长
                raw_snippet = raw_content[:500].replace('\n', ' ')
                parts.append(f"   内容片段: {raw_snippet}...")
    
    result_text = "\n".join(parts)
    
    # 截断到最大字符数
    if len(result_text) > max_chars:
        result_text = result_text[:max_chars] + "\n\n[搜索结果已截断]"
    
    return result_text


async def search_and_format(query: str, **kwargs) -> str:
    """一站式搜索+格式化"""
    data = await tavily_search(query, **kwargs)
    return format_search_results(data)
