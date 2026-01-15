import os
import time
import json
import sqlite3
import bcrypt
from openai import AsyncOpenAI
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer
import chainlit as cl
from dotenv import load_dotenv
from utils import get_thinking_content, filter_content
from config.chat_settings import get_chat_settings, get_model_config

# 加载环境变量
load_dotenv()


async def generate_chat_title(client, model_config, user_message: str, assistant_response: str):
    """
    调用模型生成简短的对话标题。
    优先尝试使用环境变量中配置的独立 '标题模型' (TITLE_MODEL_...)。
    如果没有配置，则回退使用传入的主对话模型。
    """
    
    # 1. 尝试从环境变量读取独立配置
    title_api_key = os.getenv("TITLE_MODEL_API_KEY")
    title_base_url = os.getenv("TITLE_MODEL_BASE_URL")
    title_model_name = os.getenv("TITLE_MODEL_NAME")
    
    target_client = client
    target_model = model_config["model_name"]
    # 默认给一个比较大的 max_tokens 以防主模型是 Thinking 模型
    # 如果是专用的小模型，这个值大一点也没关系，因为它不会输出废话
    target_max_tokens = 1024 

    # 2. 如果配置了独立模型，则使用独立客户端
    if title_api_key and title_base_url and title_model_name:
        # print(f"DEBUG: 使用独立的标题生成模型: {title_model_name}", flush=True)
        try:
            target_client = AsyncOpenAI(api_key=title_api_key, base_url=title_base_url)
            target_model = title_model_name
            target_max_tokens = 200 # 专用模型通常不需要思考，200够了
        except Exception as e:
            print(f"❌ 初始化独立标题模型客户端失败: {e}，回退到主模型", flush=True)
            target_client = client

    # print(f"DEBUG: 正在生成标题... 模型: {target_model}, 用户输入长度: {len(user_message)}", flush=True)
    
    try:
        response = await target_client.chat.completions.create(
            model=target_model,
            messages=[
                {
                    "role": "system", 
                    "content": "You are a title generator. Summarize a concise ENGLISH title based on the user query and assistant response. Requirements:\n1. Max 5 words\n2. Use only key terms\n3. No punctuation\n4. Prefix with a relevant emoji"
                },
                {
                    "role": "user", 
                    "content": f"用户: {user_message[:100]}\n助手: {assistant_response[:100]}"
                }
            ],
            temperature=0.7,
            max_tokens=target_max_tokens,
        )
        
        # print(f"DEBUG: 模型响应对象: {response}", flush=True)
        title = response.choices[0].message.content.strip()
        # 清理引号和Thinking内容(如果模型不支持思考但输出了类似标签)
        title = title.strip('"\'""''').split('\n')[0] 
        
        # print(f"DEBUG: 生成的标题: {title}", flush=True)
        return title
    except Exception as e:
        print(f"❌ 生成标题失败: {e}", flush=True)
        # import traceback
        # traceback.print_exc()
        return None


def authenticate_user(username: str, password: str):
    """验证用户凭据（使用数据库）"""
    db_file = "users.db"
    
    # 如果数据库不存在，检查开发模式
    if not os.path.exists(db_file):
        if os.getenv("DEV_MODE", "false").lower() == "true":
            if (username, password) == ("admin", "admin"):
                return cl.User(
                    identifier="admin", 
                    metadata={"role": "admin", "provider": "credentials"}
                )
        return None
    
    try:
        conn = sqlite3.connect(db_file)
        c = conn.cursor()
        c.execute("SELECT password_hash, role FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        conn.close()

        if user:
            stored_password_hash, role = user
            if bcrypt.checkpw(password.encode("utf-8"), stored_password_hash):
                return cl.User(
                    identifier=username, 
                    metadata={"role": role, "provider": "credentials"}
                )
    except Exception as e:
        print(f"认证错误: {e}")
    
    return None


@cl.data_layer
def get_data_layer():
    return SQLAlchemyDataLayer(
        conninfo="sqlite+aiosqlite:///mychat.db",
        storage_provider=None
    )


@cl.password_auth_callback
def auth_callback(username: str, password: str):
    """Chainlit 认证回调"""
    return authenticate_user(username, password)


@cl.on_chat_resume
async def on_chat_resume(thread):
    await get_chat_settings()
    model_config = get_model_config()
    
    client = AsyncOpenAI(
        api_key=model_config["api_key"],
        base_url=model_config["base_url"]
    )
    cl.user_session.set("client", client)
    cl.user_session.set("model_config", model_config)
    # cl.user_session.set("title_generated", True)  # DEBUG: 注释掉以便测试标题生成


@cl.on_message
async def on_message(msg: cl.Message):

    client = cl.user_session.get("client")
    model_config = cl.user_session.get("model_config")
    
    if not client or not model_config:
        await cl.Message(content="会话初始化失败，请刷新页面重试。").send()
        return
    
    start = time.time()
    is_first_message = not cl.user_session.get("title_generated", False)
    
    try:
        stream = await client.chat.completions.create(
            model=model_config["model_name"],
            messages=[
                {"role": "system", "content": "You are a helpful assistant. STOP! Read this carefully: When providing code blocks, you MUST ensure there is a blank line before the opening triple backticks (```). Never start a code block directly after a sentence without a newline."},
                *cl.chat_context.to_openai(),
            ],
            stream=True,
            temperature=model_config["temperature"],
        )

        thinking = False
        final_answer = cl.Message(content="")
        thinking_step = None
        full_response = ""  # 收集完整回复用于生成标题
        
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
                    thought_for = round(time.time() - start)
                    thinking_step.name = f"Thought for {thought_for}s"
                    await thinking_step.update()
                    await thinking_step.__aexit__(None, None, None)
                    thinking = False
                
                content = filter_content(delta.content)
                if content:
                    full_response += content
                    await final_answer.stream_token(content)

        await final_answer.send()
        
        # 首次消息：生成对话标题
        # 首次消息：生成对话标题
        if is_first_message and full_response:
            # print("DEBUG: 检测到首条消息，准备更新标题...", flush=True)
            # 异步非阻塞生成标题，避免卡顿
            # 但为了简单起见，先阻塞调用确认功能正常
            try:
                title = await generate_chat_title(client, model_config, msg.content, full_response)
                # print(f"DEBUG: generate_chat_title 返回: {title}", flush=True)
                
                if title:
                    thread_id = cl.context.session.thread_id
                    # print(f"DEBUG: 获取到 thread_id: {thread_id}", flush=True)
                    
                    data_layer = get_data_layer()
                    if data_layer and thread_id:
                        try:
                            # 尝试更新
                            await data_layer.update_thread(thread_id=thread_id, name=title)
                            # print(f"✅ 成功调用 update_thread，新标题: {title}", flush=True)
                            
                            # 发送 Toast 提示告知用户
                            await cl.Message(content=f"📝 Conversation title updated: {title}").send()
                        except Exception as e:
                            print(f"❌ 更新标题数据库失败: {e}", flush=True)
                    else:
                        print("❌ 无法更新标题: data_layer 或 thread_id 缺失", flush=True)
            except Exception as e:
                 print(f"❌ 侧边栏标题逻辑外层异常: {e}", flush=True)
                 import traceback
                 traceback.print_exc()
            cl.user_session.set("title_generated", True)
        
    except Exception as e:
        error_msg = f"请求出错: {str(e)}"
        await cl.Message(content=error_msg).send()


@cl.set_starters
async def set_starters():
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'starters.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            return [cl.Starter(**starter) for starter in config['starters']]
    except Exception as e:
        print(f"加载 starters 配置失败: {e}")
        return []


@cl.on_chat_start
async def start_chat():
    await get_chat_settings()
    model_config = get_model_config()
    
    client = AsyncOpenAI(
        api_key=model_config["api_key"],
        base_url=model_config["base_url"]
    )
    
    cl.user_session.set("client", client)
    cl.user_session.set("model_config", model_config)
    cl.user_session.set("title_generated", False)  # 新对话，标题未生成


@cl.on_settings_update
async def on_settings_update(settings):
    """当用户调整温度时更新配置"""
    model_config = get_model_config()
    # 使用用户调整后的温度
    model_config["temperature"] = settings.get("Temperature", model_config["temperature"])
    cl.user_session.set("model_config", model_config)