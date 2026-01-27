import sqlite3
import pandas as pd

def inspect_db():
    conn = sqlite3.connect('clinical_issues_v2.db')
    cursor = conn.cursor()
    
    # List all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [t[0] for t in cursor.fetchall()]
    print(f"Tables: {tables}")
    
    # Inspect issue tables
    issue_tables = [t for t in tables if t.startswith('issues_')]
    for table in issue_tables:
        count = cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"Table {table}: {count} issues")
        if count > 0:
            latest = pd.read_sql_query(f"SELECT * FROM {table} ORDER BY created_at DESC LIMIT 1", conn)
            print(f"  Latest issue in {table}: {latest['issue'].values[0]} ({latest['created_at'].values[0]})")
    
    conn.close()

if __name__ == "__main__":
    inspect_db()
