import os
import time
import json
import os.path
from openai import AsyncOpenAI
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer
import chainlit as cl
from dotenv import load_dotenv
from utils import get_thinking_content, filter_content
from config.chat_settings import get_chat_settings, get_model_config, MODEL_CONFIGS

# 初始化客户端（使用配置文件中的第一个模型作为默认值）
default_model = next(iter(MODEL_CONFIGS))
default_config = get_model_config(default_model)
client = AsyncOpenAI(
    api_key=default_config["api_key"],
    base_url=default_config["base_url"],
)
#print("Using API Key:", os.getenv("DEEP_SEEK_API_KEY"))



@cl.data_layer
def get_data_layer():
    return SQLAlchemyDataLayer(
        conninfo="sqlite+aiosqlite:///mychat.db",
        storage_provider=None
    )

# 用户认证
@cl.password_auth_callback
def auth_callback(username: str, password: str):
    # Fetch the user matching username from your database
    # and compare the hashed password with the value stored in the database
    if (username, password) == ("admin", "admin"):
        return cl.User(
            identifier="admin", metadata={"role": "admin", "provider": "credentials"}
        )
    else:
        return None


@cl.on_chat_resume
async def on_chat_resume(thread):
    settings = await get_chat_settings()
    pass


@cl.on_message
async def on_message(msg: cl.Message):
    messages = cl.chat_context.to_openai()
    print(messages)
    start = time.time()
    model_config = get_model_config(global_model_name)
    stream = await client.chat.completions.create(
        model=model_config["model_name"],
        messages=[
            {"role": "system", "content": "You are an helpful assistant"},
            *cl.chat_context.to_openai(),
        ],
        stream=True,
        temperature=model_config["temperature"],
    )

    thinking = False
    final_answer = cl.Message(content="")

    # Streaming the response
    thinking_step = None
    async for chunk in stream:
        delta = chunk.choices[0].delta
        thinking_content = get_thinking_content(delta)
        
        if thinking_content is not None:
            if not thinking_step:
                thinking_step = cl.Step(name="Thinking")
                await thinking_step.__aenter__()
            thinking = True
            await thinking_step.stream_token(thinking_content)
        elif delta.content:
            if thinking and thinking_step:
                # Exit the thinking step
                thought_for = round(time.time() - start)
                thinking_step.name = f"Thought for {thought_for}s"
                await thinking_step.update()
                await thinking_step.__aexit__(None, None, None)
                thinking = False
            
            content = filter_content(delta.content)
            if content:
                await final_answer.stream_token(content)

    await final_answer.send()




@cl.set_starters
async def set_starters():
    # 从配置文件加载启动器配置
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'starters.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            return [cl.Starter(**starter) for starter in config['starters']]
    except Exception as e:
        print(f"Error loading starters config: {e}")
        return []

# 从配置模块导入get_chat_settings函数

# 添加全局变量
global_model_name = None

@cl.on_chat_start
async def start_chat():
    settings = await get_chat_settings()
    model_name = settings['Model']
    model_config = get_model_config(model_name)
    global client, global_model_name
    global_model_name = model_name
    client = AsyncOpenAI(
        api_key=model_config["api_key"],
        base_url=model_config["base_url"]
    )
    # 发送系统消息显示当前使用的模型
    #await cl.Message(content=f"当前使用的模型: {model_name}", author="Assistant").send()

@cl.on_settings_update
async def on_settings_update(settings):
    model_name = settings['Model']
    model_config = get_model_config(model_name)
    global client, global_model_name
    global_model_name = model_name
    client = AsyncOpenAI(
        api_key=model_config["api_key"],
        base_url=model_config["base_url"]
    )
    # 发送系统消息显示模型已更新
    #await cl.Message(content=f"模型已更新为: {model_name}", author="System").send()