"""思考内容处理工具函数"""

import re


def get_thinking_content(delta):
    """从模型响应中获取思考内容
    
    支持两种格式：
    1. reasoning_content 属性（DeepSeek 等模型）
    2. <think>...</think> 标签格式
    
    Args:
        delta: 模型响应的 delta 对象
        
    Returns:
        str | None: 思考内容，如果没有则返回 None
    """
    # 优先检查 reasoning_content 属性
    reasoning_content = getattr(delta, "reasoning_content", None)
    if reasoning_content:
        return reasoning_content
    
    # 检查 content 中的 <think> 标签
    content = getattr(delta, "content", None)
    if content and "<think>" in content:
        # 提取 <think> 标签之间的内容
        match = re.search(r'<think>(.*?)</think>', content, re.DOTALL)
        if match:
            return match.group(1)
    
    return None


def filter_content(content):
    """过滤掉思考标签，保留正常内容
    
    Args:
        content: 原始内容字符串
        
    Returns:
        str: 过滤后的内容
    """
    if not content:
        return ""
    
    # 移除 <think>...</think> 标签及其内容
    filtered = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
    
    # 移除可能残留的未闭合标签
    filtered = filtered.replace("<think>", "").replace("</think>", "")
    
    return filtered if filtered else ""