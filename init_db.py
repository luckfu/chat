"""初始化 Chainlit 聊天数据库表（完整版）"""
import sqlite3
import os

db_file = "mychat.db"

# 如果存在旧数据库，先删除
if os.path.exists(db_file):
    os.remove(db_file)
    print(f"已删除旧数据库 '{db_file}'")

print(f"正在初始化 Chainlit 数据库 '{db_file}'...")

conn = sqlite3.connect(db_file)
cursor = conn.cursor()

# 创建 Chainlit SQLAlchemy 数据层所需的表（完整字段版本）
tables = [
    '''
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        identifier TEXT UNIQUE NOT NULL,
        "createdAt" TEXT,
        metadata TEXT
    )
    ''',
    '''
    CREATE TABLE IF NOT EXISTS threads (
        id TEXT PRIMARY KEY,
        "createdAt" TEXT,
        name TEXT,
        "userId" TEXT,
        "userIdentifier" TEXT,
        tags TEXT,
        metadata TEXT,
        FOREIGN KEY ("userId") REFERENCES users(id)
    )
    ''',
    '''
    CREATE TABLE IF NOT EXISTS steps (
        id TEXT PRIMARY KEY,
        "threadId" TEXT,
        "parentId" TEXT,
        "createdAt" TEXT,
        "start" TEXT,
        "end" TEXT,
        name TEXT,
        type TEXT,
        input TEXT,
        output TEXT,
        streaming INTEGER,
        "isError" INTEGER,
        "waitForAnswer" INTEGER,
        "defaultOpen" INTEGER,
        "showInput" TEXT,
        metadata TEXT,
        generation TEXT,
        language TEXT,
        tags TEXT,
        FOREIGN KEY ("threadId") REFERENCES threads(id)
    )
    ''',
    '''
    CREATE TABLE IF NOT EXISTS elements (
        id TEXT PRIMARY KEY,
        "threadId" TEXT,
        "stepId" TEXT,
        name TEXT,
        type TEXT,
        display TEXT,
        size TEXT,
        language TEXT,
        page TEXT,
        url TEXT,
        path TEXT,
        mime TEXT,
        "objectKey" TEXT,
        "forId" TEXT,
        "chainlitKey" TEXT,
        props TEXT,
        FOREIGN KEY ("threadId") REFERENCES threads(id),
        FOREIGN KEY ("stepId") REFERENCES steps(id)
    )
    ''',
    '''
    CREATE TABLE IF NOT EXISTS feedbacks (
        id TEXT PRIMARY KEY,
        "stepId" TEXT,
        "forId" TEXT,
        value INTEGER,
        comment TEXT,
        FOREIGN KEY ("stepId") REFERENCES steps(id)
    )
    '''
]

for table_sql in tables:
    cursor.execute(table_sql)
    
conn.commit()
conn.close()

print(f"✅ 数据库 '{db_file}' 初始化完成！")
print("   已创建表: users, threads, steps, elements, feedbacks")
