import sqlite3
conn = sqlite3.connect("db/company.db")
rows = conn.execute("SELECT * FROM appointments").fetchall()
print(rows)
conn.close()