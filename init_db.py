import sqlite3
import os
from datetime import datetime

def init_db():
    """Inicializa o banco de dados com as tabelas necessárias"""
    # Define o caminho do banco de dados
    DATABASE = os.environ.get('DB_PATH', 'financas.db')
    
    # Garante que o diretório do banco de dados existe
    db_dir = os.path.dirname(os.path.abspath(DATABASE))
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    
    # Tabela de usuários
    conn.execute('''
        CREATE TABLE IF NOT EXISTS usuario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            nome_completo TEXT,
            email TEXT,
            ativo BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabela de categorias de receitas
    conn.execute('''
        CREATE TABLE IF NOT EXISTS categoria_receita (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            descricao TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            usuario_id INTEGER
        )
    ''')
    
    # Tabela de subcategorias de receitas
    conn.execute('''
        CREATE TABLE IF NOT EXISTS subcategoria_receita (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            categoria_id INTEGER NOT NULL,
            descricao TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            usuario_id INTEGER,
            FOREIGN KEY (categoria_id) REFERENCES categoria_receita (id)
        )
    ''')
    
    # Tabela de categorias de despesas
    conn.execute('''
        CREATE TABLE IF NOT EXISTS categoria_despesa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            descricao TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            usuario_id INTEGER
        )
    ''')
    
    # Tabela de subcategorias de despesas
    conn.execute('''
        CREATE TABLE IF NOT EXISTS subcategoria_despesa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            categoria_id INTEGER NOT NULL,
            descricao TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            usuario_id INTEGER,
            FOREIGN KEY (categoria_id) REFERENCES categoria_despesa (id)
        )
    ''')
    
    # Tabela de receitas
    conn.execute('''
        CREATE TABLE IF NOT EXISTS receita (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            categoria_id INTEGER NOT NULL,
            subcategoria_id INTEGER,
            data_inicio DATE NOT NULL,
            data_fim DATE,
            tipo_recorrencia TEXT NOT NULL DEFAULT 'mensal',
            dia_comum_recebimento INTEGER,
            valor REAL NOT NULL,
            numero_parcelas TEXT NOT NULL DEFAULT '1',
            parcela_atual INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            usuario_id INTEGER,
            fixo BOOLEAN DEFAULT 0,
            pago BOOLEAN DEFAULT 0,
            FOREIGN KEY (categoria_id) REFERENCES categoria_receita (id),
            FOREIGN KEY (subcategoria_id) REFERENCES subcategoria_receita (id)
        )
    ''')
    
    # Tabela de despesas
    conn.execute('''
        CREATE TABLE IF NOT EXISTS despesa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            categoria_id INTEGER NOT NULL,
            subcategoria_id INTEGER,
            data_inicio DATE NOT NULL,
            data_fim DATE,
            tipo_recorrencia TEXT NOT NULL DEFAULT 'mensal',
            numero_parcelas TEXT NOT NULL DEFAULT '1',
            parcela_atual INTEGER DEFAULT 1,
            dia_comum_pagamento INTEGER,
            valor REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            usuario_id INTEGER,
            fixo BOOLEAN DEFAULT 0,
            pago BOOLEAN DEFAULT 0,
            FOREIGN KEY (categoria_id) REFERENCES categoria_despesa (id),
            FOREIGN KEY (subcategoria_id) REFERENCES subcategoria_despesa (id)
        )
    ''')
    
    # Inserir dados iniciais se não existirem
    cursor = conn.cursor()
    
    # Verificar se já existem categorias de receita
    cursor.execute('SELECT COUNT(*) FROM categoria_receita')
    if cursor.fetchone()[0] == 0:
        # Categorias de receita iniciais
        conn.execute("INSERT INTO categoria_receita (nome, descricao) VALUES ('Salário', 'Salário mensal')")
        conn.execute("INSERT INTO categoria_receita (nome, descricao) VALUES ('Freelance', 'Trabalhos freelance')")
        conn.execute("INSERT INTO categoria_receita (nome, descricao) VALUES ('Investimentos', 'Rendimentos de investimentos')")
        conn.execute("INSERT INTO categoria_receita (nome, descricao) VALUES ('Outros', 'Outras receitas')")
        
        # Subcategorias de receita iniciais
        conn.execute("INSERT INTO subcategoria_receita (nome, categoria_id) VALUES ('Credicaf', 1)")
        conn.execute("INSERT INTO subcategoria_receita (nome, categoria_id) VALUES ('Projetos Web', 2)")
        conn.execute("INSERT INTO subcategoria_receita (nome, categoria_id) VALUES ('Consultoria', 2)")
        conn.execute("INSERT INTO subcategoria_receita (nome, categoria_id) VALUES ('Ações', 3)")
        conn.execute("INSERT INTO subcategoria_receita (nome, categoria_id) VALUES ('Renda Fixa', 3)")
    
    # Verificar se já existem categorias de despesa
    cursor.execute('SELECT COUNT(*) FROM categoria_despesa')
    if cursor.fetchone()[0] == 0:
        # Categorias de despesa iniciais
        conn.execute("INSERT INTO categoria_despesa (nome, descricao) VALUES ('Alimentação', 'Gastos com comida')")
        conn.execute("INSERT INTO categoria_despesa (nome, descricao) VALUES ('Transporte', 'Gastos com transporte')")
        conn.execute("INSERT INTO categoria_despesa (nome, descricao) VALUES ('Moradia', 'Gastos com habitação')")
        conn.execute("INSERT INTO categoria_despesa (nome, descricao) VALUES ('Entretenimento', 'Gastos com lazer')")
        conn.execute("INSERT INTO categoria_despesa (nome, descricao) VALUES ('Saúde', 'Gastos com saúde')")
        conn.execute("INSERT INTO categoria_despesa (nome, descricao) VALUES ('Outros', 'Outras despesas')")
        
        # Subcategorias de despesa iniciais
        conn.execute("INSERT INTO subcategoria_despesa (nome, categoria_id) VALUES ('Supermercado', 1)")
        conn.execute("INSERT INTO subcategoria_despesa (nome, categoria_id) VALUES ('Restaurante', 1)")
        conn.execute("INSERT INTO subcategoria_despesa (nome, categoria_id) VALUES ('Gasolina', 2)")
        conn.execute("INSERT INTO subcategoria_despesa (nome, categoria_id) VALUES ('Transporte Público', 2)")
        conn.execute("INSERT INTO subcategoria_despesa (nome, categoria_id) VALUES ('Aluguel', 3)")
        conn.execute("INSERT INTO subcategoria_despesa (nome, categoria_id) VALUES ('Energia', 3)")
        conn.execute("INSERT INTO subcategoria_despesa (nome, categoria_id) VALUES ('Água', 3)")
        conn.execute("INSERT INTO subcategoria_despesa (nome, categoria_id) VALUES ('Cinema', 4)")
        conn.execute("INSERT INTO subcategoria_despesa (nome, categoria_id) VALUES ('Streaming', 4)")
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Banco de dados inicializado com sucesso!")