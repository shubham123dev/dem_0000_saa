import sqlite3

con = sqlite3.connect("workplace_sandbox.db")
cur = con.cursor()

print("--- agent_conversations columns ---")
for r in cur.execute("PRAGMA table_info(agent_conversations)"):
    print(r[1], r[2])

print("--- alembic_version ---")
try:
    for r in cur.execute("select version_num from alembic_version"):
        print(r)
except Exception as e:
    print("no alembic_version table:", e)

print("--- agent_context_blocks columns ---")
for r in cur.execute("PRAGMA table_info(agent_context_blocks)"):
    print(r[1], r[2])

con.close()
