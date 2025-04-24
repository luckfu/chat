import os
import time
import json
import os.path
import bcrypt
import sqlite3
import aiohttp
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer
import chainlit as cl
from dotenv import load_dotenv
from utils import get_thinking_content, filter_content
from config.chat_settings import get_chat_settings, get_model_config, MODEL_CONFIGS

load_dotenv()

# Langflow API 配置
BASE_API_URL = os.getenv("LANGFLOW_BASE_URL", "http://127.0.0.1:7860")
FLOW_ID = os.getenv("FLOW_ID")
LANGFLOW_API_KEY = os.getenv("LANGFLOW_API_KEY")

# Remove the OpenAI client initialization since we're using Langflow

def authenticate_user(username: str, password: str):
    """验证用户凭据"""
    conn = sqlite3.connect("users.db")
    c = conn.cursor()

    c.execute("SELECT password_hash, role FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    conn.close()

    if user:
        stored_password_hash, role = user
        if bcrypt.checkpw(password.encode("utf-8"), stored_password_hash):
            return cl.User(identifier=username, metadata={"role": role, "provider": "credentials"})

    return None

@cl.data_layer
def get_data_layer():
    return SQLAlchemyDataLayer(
        conninfo="sqlite+aiosqlite:///mychat.db",
        storage_provider=None
    )

# 用户认证
@cl.password_auth_callback
def auth_callback(username: str, password: str):
    """Chainlit 认证回调"""
    return authenticate_user(username, password)


@cl.on_chat_resume
async def on_chat_resume(thread):
    settings = await get_chat_settings()
    pass


@cl.on_message
async def on_message(msg: cl.Message):
    messages = cl.chat_context.to_openai()
    print("Historical messages:", messages)
    start = time.time()
    
    url = f"{BASE_API_URL}/api/v1/run/{FLOW_ID}?stream=true"
    payload = {
        "input_value": msg.content,
        "output_type": "chat",
        "input_type": "chat"
    }
    
    print(f"Request URL: {url}")
    print(f"Request payload: {json.dumps(payload, ensure_ascii=False)}")
    
    thinking = False
    final_answer = cl.Message(content="")
    thinking_step = None
    
    async with aiohttp.ClientSession() as session:
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {LANGFLOW_API_KEY}" 
            }
            
            async with session.post(url, json=payload, headers=headers) as response:
                print(f"Response status: {response.status}")
                
                if response.status != 200:
                    error_text = await response.text()
                    print(f"Error response: {error_text}")
                    raise Exception(f"API request failed: {response.status} - {error_text}")
                
                buffer = ""
                async for line in response.content:
                    if not line:
                        continue
                        
                    try:
                        line_text = line.decode('utf-8').strip()
                        if not line_text:
                            continue
                            
                        event_data = json.loads(line_text)
                        event_type = event_data["event"]
                        
                        if event_type == "add_message":
                            message_id = event_data["data"]["id"]
                            
                        elif event_type == "token":
                            chunk = event_data["data"].get("chunk", "")
                            if chunk:  # 过滤空心跳包
                                try:
                                    # 首先尝试直接解码
                                    decoded = chunk
                                    if '\\u' in chunk:
                                        decoded = chunk.encode().decode('unicode_escape')
                                        
                                    # 使用 get_thinking_content 检查是否包含思考内容
                                    thinking_content = get_thinking_content(type('Delta', (), {'content': decoded})())
                                    
                                    if thinking_content:
                                        # 如果有思考内容，创建或更新 thinking_step
                                        if not thinking_step:
                                            thinking_step = cl.Step(name="Thinking")
                                            await thinking_step.__aenter__()
                                            thinking = True
                                        await thinking_step.stream_token(thinking_content)
                                    else:
                                        # 如果没有思考内容，使用 filter_content 处理普通内容
                                        filtered_content = filter_content(decoded)
                                        if filtered_content:
                                            buffer += filtered_content
                                            await final_answer.stream_token(filtered_content)
                                            
                                except Exception as decode_error:
                                    print(f"解码错误: {decode_error}, 原始chunk: {chunk}")
                                    
                        elif event_type == "end":
                            if thinking and thinking_step:
                                thought_for = round(time.time() - start)
                                thinking_step.name = f"Thought for {thought_for}s"
                                await thinking_step.update()
                                await thinking_step.__aexit__(None, None, None)
                                thinking = False
                            
                            # 设置最终答案
                            final_answer.content = buffer
                            await final_answer.send()
                            
                    except json.JSONDecodeError as e:
                        print(f"解析失败的行: {line_text}, 错误: {str(e)}")
                        continue
                        
        except Exception as e:
            print(f"请求错误: {str(e)}")
            await cl.Message(content=f"抱歉，发生错误: {str(e)}").send()


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
    # We don't need to initialize OpenAI client anymore
    # Just store the settings if needed for future use
    pass

@cl.on_settings_update
async def on_settings_update(settings):
    # We don't need to update OpenAI client anymore
    # Just store the settings if needed for future use
    pass