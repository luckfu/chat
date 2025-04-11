import chainlit as cl
from chainlit.input_widget import Select, Switch, Slider

import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 获取API密钥
DEEP_SEEK_API_KEY = os.getenv("DEEP_SEEK_API_KEY")
QWQ_API_KEY = os.getenv("QWQ_API_KEY")

# 获取API基础URL
BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8080")

# 模型配置映射
MODEL_CONFIGS = {
    "qwq-32b": {
        "base_url": BASE_URL,
        "model_name": "qwq-32b",
        "temperature": 0.7,
        "api_key": QWQ_API_KEY
    },
    "DeepSeek-R1": {
        "base_url": BASE_URL,
        "model_name": "Pro/deepseek-ai/DeepSeek-R1",
        "temperature": 0.7,
        "api_key": DEEP_SEEK_API_KEY
    },
    "DeepSeek-V3": {
        "base_url": BASE_URL,
        "model_name": "Pro/deepseek-ai/DeepSeek-V3",
        "temperature": 0.7,
        "api_key": DEEP_SEEK_API_KEY
    }
}

# 聊天设置配置
CHAT_SETTINGS = [
    Select(
        id="Model",
        label="OpenAI - Model",
        values=["qwq-32b", "DeepSeek-R1", "DeepSeek-V3"],
        initial_index=0,
    ),
    Switch(id="Streaming", label="OpenAI - Stream Tokens", initial=True),
    Slider(
        id="Temperature",
        label="LLM - Temperature",
        initial=MODEL_CONFIGS[next(iter(MODEL_CONFIGS))]["temperature"],
        min=0,
        max=1,
        step=0.05,
    )
    ##Slider(
    ##    id="SAI_Steps",
    ##    label="Stability AI - Steps",
    ##    initial=30,
    ##    min=10,
    ##    max=150,
    ##    step=1,
    ##    description="Amount of inference steps performed on image generation.",
    ##),
    ##Slider(
    ##    id="SAI_Cfg_Scale",
    ##    label="Stability AI - Cfg_Scale",
    ##    initial=7,
    ##    min=1,
    ##    max=35,
    ##    step=0.1,
    ##    description="Influences how strongly your generation is guided to match your prompt.",
    ##),
    ##Slider(
    ##    id="SAI_Width",
    ##    label="Stability AI - Image Width",
    ##    initial=512,
    ##    min=256,
    ##    max=2048,
    ##    step=64,
    ##    tooltip="Measured in pixels",
    ##),
    ##Slider(
    ##    id="SAI_Height",
    ##    label="Stability AI - Image Height",
    ##    initial=512,
    ##    min=256,
    ##    max=2048,
    ##    step=64,
    ##    tooltip="Measured in pixels",
    ##),
]

async def get_chat_settings():
    settings = await cl.ChatSettings(CHAT_SETTINGS).send()
    return settings

def get_model_config(model_name):
    # 获取配置文件中的第一个模型名作为默认值
    default_model = next(iter(MODEL_CONFIGS))
    return MODEL_CONFIGS.get(model_name, MODEL_CONFIGS[default_model])