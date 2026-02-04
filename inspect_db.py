
import sqlite3
import os

DATABASE = 'financas.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def print_table_info(table_name):
    conn = get_db_connection()
    print(f"--- Table: {table_name} ---")
    try:
        cursor = conn.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        for col in columns:
            print(f"{col['name']} ({col['type']})")
    except Exception as e:
        print(f"Error: {e}")
    conn.close()
    print("\n")

if __name__ == "__main__":
    tables = ['despesa', 'cartao_credito', 'instituicao_financeira', 'categoria_despesa', 'subcategoria_despesa']
    for t in tables:
        print_table_info(t)
