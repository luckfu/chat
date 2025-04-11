def get_thinking_content(delta):
    """从模型响应中获取思考内容"""
    # 尝试获取 reasoning_content
    reasoning_content = getattr(delta, "reasoning_content", None)
    if reasoning_content is not None:
        return reasoning_content
    
    # 尝试获取 content 中的 <think> 标记内容
    content = getattr(delta, "content", None)
    if content and "<think>" in content:
        # 提取 <think> 标记之间的内容
        start = content.find("<think>") + 7
        end = content.find("</think>")
        if end > start:
            return content[start:end]
    
    return None

def filter_content(content):
    """只过滤掉</think>标签，保持其他内容不变"""
    if not content:
        return ""
    
    # 只移除</think>标签
    if "</think>" in content:
        content = content.replace("</think>", "")

    # 只移除</think>标签
    if "<think>" in content:
        content = content.replace("<think>", "")
    
    return content