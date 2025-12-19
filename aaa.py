import sqlite3

db_path = r"F:\python\pppppppppppppppppppppycharm\项目\server_data\记忆.db"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

print("原始消息条数 =", conn.execute("SELECT COUNT(*) AS n FROM 原始消息").fetchone()["n"])
print("会话摘要条数 =", conn.execute("SELECT COUNT(*) AS n FROM 会话摘要").fetchone()["n"])

print("\n=== 最近 10 条原始消息 ===")
for r in conn.execute("SELECT 时间戳, 角色, 文本 FROM 原始消息 ORDER BY 时间戳 DESC LIMIT 10"):
    print(r["时间戳"], r["角色"], r["文本"][:80])

print("\n=== 最近 3 条摘要 ===")
for r in conn.execute("SELECT 时间戳, 摘要 FROM 会话摘要 ORDER BY 时间戳 DESC LIMIT 3"):
    print(r["时间戳"], r["摘要"][:200], "\n")