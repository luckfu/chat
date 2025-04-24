import sqlite3
import bcrypt
import os

db_file = "users.db"
# --- 在这里设置你想要创建的用户名和密码 ---
username_to_create = "admin"
password_to_create = "password123" # 请使用一个强密码
role_to_assign = "admin" # 或 'user' 等
# -----------------------------------------

# 检查 bcrypt 是否安装，如果你的 LangflowChat.py 能运行，应该已经安装了
try:
    import bcrypt
except ImportError:
    print("错误：bcrypt 库未安装。请运行 'pip install bcrypt'")
    exit(1)

print(f"正在初始化数据库 '{db_file}'...")

# Hash the password
password_bytes = password_to_create.encode('utf-8')
salt = bcrypt.gensalt()
hashed_password = bcrypt.hashpw(password_bytes, salt)

# Connect to the database (creates if not exists)
conn = None
try:
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # Create the users table if it doesn't exist
    print("正在创建 'users' 表 (如果不存在)...")
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password_hash BLOB NOT NULL,
        role TEXT NOT NULL
    )
    ''')
    print("'users' 表已准备就绪。")

    # Insert or update the user data
    print(f"正在尝试添加/更新用户 '{username_to_create}'...")
    try:
        cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                       (username_to_create, hashed_password, role_to_assign))
        print(f"用户 '{username_to_create}' 创建成功。")
    except sqlite3.IntegrityError:
        print(f"用户 '{username_to_create}' 已存在。正在更新密码和角色...")
        cursor.execute("UPDATE users SET password_hash = ?, role = ? WHERE username = ?",
                       (hashed_password, role_to_assign, username_to_create))
        print(f"用户 '{username_to_create}' 更新成功。")

    # Commit changes
    conn.commit()
    print("更改已提交。")

except sqlite3.Error as e:
    print(f"数据库操作时发生错误: {e}")
finally:
    if conn:
        conn.close()
        print(f"数据库连接已关闭。")

print(f"数据库 '{db_file}' 初始化/更新完成。")