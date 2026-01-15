import chainlit as cl
from chainlit.input_widget import Slider
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# ===== 简化配置：从环境变量读取 =====
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
API_KEY = os.getenv("API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))

# 验证 API Key 配置
if not API_KEY:
    print("⚠️ 警告: API_KEY 未配置，请在 .env 文件中设置")

# 聊天设置配置 (只保留温度调节)
CHAT_SETTINGS = [
    Slider(
        id="Temperature",
        label="温度 (Temperature)",
        initial=TEMPERATURE,
        min=0,
        max=1,
        step=0.05,
        description="控制输出的随机性，值越高输出越随机",
    )
]


async def get_chat_settings():
    """获取聊天设置"""
    settings = await cl.ChatSettings(CHAT_SETTINGS).send()
    return settings


def get_model_config():
    """获取模型配置（简化版：直接从环境变量读取）"""
    return {
        "base_url": API_BASE_URL,
        "api_key": API_KEY,
        "model_name": MODEL_NAME,
        "temperature": TEMPERATURE,
    }