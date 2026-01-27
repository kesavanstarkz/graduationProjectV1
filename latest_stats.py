import sqlite3
import pandas as pd

def get_latest_stats():
    conn = sqlite3.connect('clinical_issues_v2.db')
    cursor = conn.cursor()
    
    # Get the latest table by creation time of its records
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'issues_%';")
    tables = [t[0] for t in cursor.fetchall()]
    
    latest_table = None
    latest_time = None
    
    for table in tables:
        try:
            res = cursor.execute(f"SELECT MAX(created_at) FROM {table}").fetchone()[0]
            if res and (latest_time is None or res > latest_time):
                latest_time = res
                latest_table = table
        except:
            continue
            
    if not latest_table:
        print("No datasets found.")
        return

    print(f"Dataset: {latest_table}")
    df = pd.read_sql_query(f"SELECT * FROM {latest_table}", conn)
    print(f"Total Issues: {len(df)}")
    print(f"Records Affected: {df['row_number'].nunique()}")
    print("Severity Distribution:")
    print(df['severity'].value_counts().to_dict())
    
    conn.close()

if __name__ == "__main__":
    get_latest_stats()
