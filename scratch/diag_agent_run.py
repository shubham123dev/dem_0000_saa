import sqlite3

con = sqlite3.connect("workplace_sandbox.db")
cur = con.cursor()

print("--- triggers ---")
for r in cur.execute("select name, tbl_name from sqlite_master where type='trigger'"):
    print(r)

print("--- agent/fts tables ---")
for r in cur.execute(
    "select name from sqlite_master where type='table' and (name like 'agent%' or name like '%fts%')"
):
    print(r)

print("--- org_sandbox_001 ---")
for r in cur.execute("select id, status from organizations where id='org_sandbox_001'"):
    print(r)

print("--- membership 215 ---")
for r in cur.execute(
    "select id, organization_id, user_id, role, membership_status from organization_memberships where user_id='215'"
):
    print(r)

con.close()
