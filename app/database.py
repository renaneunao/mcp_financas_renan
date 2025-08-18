import sqlite3
import os
from datetime import datetime

DATABASE = 'financas.db'

def get_db_connection():
    """Conecta ao banco de dados SQLite"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def migrate_database(conn):
    """Migra o banco de dados para a nova estrutura - adiciona colunas necessárias"""
    cursor = conn.cursor()
    
    # Adicionar coluna usuario_id na tabela receita se não existir
    try:
        cursor.execute("ALTER TABLE receita ADD COLUMN usuario_id INTEGER")
    except sqlite3.OperationalError:
        pass  # Coluna já existe
    
    # Adicionar coluna fixo na tabela receita se não existir
    try:
        cursor.execute("ALTER TABLE receita ADD COLUMN fixo BOOLEAN DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # Coluna já existe
        
    # Adicionar coluna usuario_id na tabela despesa se não existir
    try:
        cursor.execute("ALTER TABLE despesa ADD COLUMN usuario_id INTEGER")
    except sqlite3.OperationalError:
        pass  # Coluna já existe
    
    # Adicionar coluna fixo na tabela despesa se não existir
    try:
        cursor.execute("ALTER TABLE despesa ADD COLUMN fixo BOOLEAN DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # Coluna já existe
    
    conn.commit()

def init_db():
    """Inicializa o banco de dados com as tabelas necessárias"""
    conn = get_db_connection()
    
    # Migrar estrutura existente se necessário
    migrate_database(conn)
    
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

def get_categorias_receitas(usuario_id=None):
    """Retorna todas as categorias de receitas do usuário"""
    conn = get_db_connection()
    if usuario_id:
        categorias = conn.execute('SELECT * FROM categoria_receita WHERE usuario_id = ? ORDER BY nome', (usuario_id,)).fetchall()
    else:
        categorias = conn.execute('SELECT * FROM categoria_receita ORDER BY nome').fetchall()
    conn.close()
    return categorias

def get_subcategorias_receitas(categoria_id=None, usuario_id=None):
    """Retorna subcategorias de receitas, opcionalmente filtradas por categoria e usuário"""
    conn = get_db_connection()
    if categoria_id and usuario_id:
        subcategorias = conn.execute(
            'SELECT * FROM subcategoria_receita WHERE categoria_id = ? AND usuario_id = ? ORDER BY nome',
            (categoria_id, usuario_id)
        ).fetchall()
    elif usuario_id:
        subcategorias = conn.execute(
            '''SELECT sr.*, cr.nome as categoria_nome 
               FROM subcategoria_receita sr 
               JOIN categoria_receita cr ON sr.categoria_id = cr.id 
               WHERE sr.usuario_id = ? AND cr.usuario_id = ?
               ORDER BY cr.nome, sr.nome''',
            (usuario_id, usuario_id)
        ).fetchall()
    elif categoria_id:
        subcategorias = conn.execute(
            'SELECT * FROM subcategoria_receita WHERE categoria_id = ? ORDER BY nome',
            (categoria_id,)
        ).fetchall()
    else:
        subcategorias = conn.execute(
            '''SELECT sr.*, cr.nome as categoria_nome 
               FROM subcategoria_receita sr 
               JOIN categoria_receita cr ON sr.categoria_id = cr.id 
               ORDER BY cr.nome, sr.nome'''
        ).fetchall()
    conn.close()
    return subcategorias

def get_categorias_despesas(usuario_id=None):
    """Retorna todas as categorias de despesas do usuário"""
    conn = get_db_connection()
    if usuario_id:
        categorias = conn.execute('SELECT * FROM categoria_despesa WHERE usuario_id = ? ORDER BY nome', (usuario_id,)).fetchall()
    else:
        categorias = conn.execute('SELECT * FROM categoria_despesa ORDER BY nome').fetchall()
    conn.close()
    return categorias

def get_subcategorias_despesas(categoria_id=None, usuario_id=None):
    """Retorna subcategorias de despesas, opcionalmente filtradas por categoria e usuário"""
    conn = get_db_connection()
    if categoria_id and usuario_id:
        subcategorias = conn.execute(
            'SELECT * FROM subcategoria_despesa WHERE categoria_id = ? AND usuario_id = ? ORDER BY nome',
            (categoria_id, usuario_id)
        ).fetchall()
    elif usuario_id:
        subcategorias = conn.execute(
            '''SELECT sd.*, cd.nome as categoria_nome 
               FROM subcategoria_despesa sd 
               JOIN categoria_despesa cd ON sd.categoria_id = cd.id 
               WHERE sd.usuario_id = ? AND cd.usuario_id = ?
               ORDER BY cd.nome, sd.nome''',
            (usuario_id, usuario_id)
        ).fetchall()
    elif categoria_id:
        subcategorias = conn.execute(
            'SELECT * FROM subcategoria_despesa WHERE categoria_id = ? ORDER BY nome',
            (categoria_id,)
        ).fetchall()
    else:
        subcategorias = conn.execute(
            '''SELECT sd.*, cd.nome as categoria_nome 
               FROM subcategoria_despesa sd 
               JOIN categoria_despesa cd ON sd.categoria_id = cd.id 
               ORDER BY cd.nome, sd.nome'''
        ).fetchall()
    conn.close()
    return subcategorias

def calcular_numero_parcelas(data_inicio, data_fim, tipo_recorrencia):
    """Calcula o número de parcelas baseado no tipo de recorrência e intervalo de datas"""
    from datetime import datetime
    from dateutil.relativedelta import relativedelta
    
    if not data_fim:
        return 'x'  # Infinito se não há data fim
    
    data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
    data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d').date()
    
    # Mapeamento de tipos para incrementos
    incrementos = {
        'semanal': lambda d: d + relativedelta(weeks=1),
        'quinzenal': lambda d: d + relativedelta(weeks=2),
        'mensal': lambda d: d + relativedelta(months=1),
        'bimestral': lambda d: d + relativedelta(months=2),
        'trimestral': lambda d: d + relativedelta(months=3),
        'quadrimestral': lambda d: d + relativedelta(months=4),
        'semestral': lambda d: d + relativedelta(months=6),
        'anual': lambda d: d + relativedelta(years=1)
    }
    
    if tipo_recorrencia not in incrementos:
        return '1'
    
    # Contar quantas vezes o tipo de recorrência acontece no intervalo
    contador = 0
    data_atual = data_inicio_obj
    incremento_func = incrementos[tipo_recorrencia]
    
    while data_atual <= data_fim_obj:
        contador += 1
        data_atual = incremento_func(data_atual)
        
        # Proteção contra loops infinitos
        if contador > 1000:
            break
    
    return str(contador)

def gerar_parcelas_receita(categoria_id, subcategoria_id, data_inicio, data_fim, tipo_recorrencia, valor_parcela, dia_comum, user_id, fixo=False):
    """Gera parcelas individuais para uma receita"""
    from datetime import datetime
    from dateutil.relativedelta import relativedelta
    
    conn = get_db_connection()
    
    # Se for tipo único, inserir apenas um registro
    if tipo_recorrencia == 'unica':
        cursor = conn.execute('''
            INSERT INTO receita (categoria_id, subcategoria_id, data_inicio, valor, tipo_recorrencia, numero_parcelas, parcela_atual, usuario_id, fixo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (categoria_id, subcategoria_id, data_inicio, valor_parcela, 'unica', '1', 1, user_id, fixo))
        
        conn.commit()
        conn.close()
        return [cursor.lastrowid]
    
    # Calcular número de parcelas baseado no tipo de recorrência
    numero_parcelas = calcular_numero_parcelas(data_inicio, data_fim, tipo_recorrencia)
    
    # Mapeamento de tipos para incrementos
    incrementos = {
        'semanal': lambda d: d + relativedelta(weeks=1),
        'quinzenal': lambda d: d + relativedelta(weeks=2),
        'mensal': lambda d: d + relativedelta(months=1),
        'bimestral': lambda d: d + relativedelta(months=2),
        'trimestral': lambda d: d + relativedelta(months=3),
        'quadrimestral': lambda d: d + relativedelta(months=4),
        'semestral': lambda d: d + relativedelta(months=6),
        'anual': lambda d: d + relativedelta(years=1)
    }
    
    # Determinar quantas parcelas gerar
    if numero_parcelas == 'x':
        parcelas_a_gerar = 60  # Gerar 60 períodos para infinitas
    else:
        parcelas_a_gerar = int(numero_parcelas)
    
    # Gerar parcelas individuais (sem registro pai)
    data_atual = datetime.strptime(data_inicio, '%Y-%m-%d').date()
    if data_fim:
        data_limite = datetime.strptime(data_fim, '%Y-%m-%d').date()
    else:
        data_limite = None
    
    incremento_func = incrementos.get(tipo_recorrencia, incrementos['mensal'])
    parcelas_criadas = []
    
    for i in range(parcelas_a_gerar):
        # Se há data fim e passamos dela, parar
        if data_limite and data_atual > data_limite:
            break
            
        # Ajustar dia se especificado
        if dia_comum:
            try:
                data_atual = data_atual.replace(day=dia_comum)
            except ValueError:
                # Dia não existe no mês (ex: 31 em fevereiro)
                pass
        
        # Inserir parcela individual
        cursor = conn.execute('''
            INSERT INTO receita (categoria_id, subcategoria_id, data_inicio, valor, tipo_recorrencia, numero_parcelas, parcela_atual, dia_comum_recebimento, usuario_id, fixo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (categoria_id, subcategoria_id, data_atual.strftime('%Y-%m-%d'), valor_parcela, tipo_recorrencia, numero_parcelas, i+1, dia_comum, user_id, fixo))
        
        parcelas_criadas.append(cursor.lastrowid)
        
        # Próximo período baseado no tipo de recorrência
        data_atual = incremento_func(data_atual)
    
    conn.commit()
    conn.close()
    return parcelas_criadas

def gerar_parcelas_despesa(categoria_id, subcategoria_id, data_inicio, data_fim, tipo_recorrencia, valor_parcela, dia_comum, user_id, fixo=False):
    """Gera parcelas individuais para uma despesa"""
    from datetime import datetime
    from dateutil.relativedelta import relativedelta
    
    conn = get_db_connection()
    
    # Se for tipo único, inserir apenas um registro
    if tipo_recorrencia == 'unica':
        cursor = conn.execute('''
            INSERT INTO despesa (categoria_id, subcategoria_id, data_inicio, valor, tipo_recorrencia, numero_parcelas, parcela_atual, usuario_id, fixo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (categoria_id, subcategoria_id, data_inicio, valor_parcela, 'unica', '1', 1, user_id, fixo))
        
        conn.commit()
        conn.close()
        return [cursor.lastrowid]
    
    # Calcular número de parcelas baseado no tipo de recorrência
    numero_parcelas = calcular_numero_parcelas(data_inicio, data_fim, tipo_recorrencia)
    
    # Mapeamento de tipos para incrementos
    incrementos = {
        'semanal': lambda d: d + relativedelta(weeks=1),
        'quinzenal': lambda d: d + relativedelta(weeks=2),
        'mensal': lambda d: d + relativedelta(months=1),
        'bimestral': lambda d: d + relativedelta(months=2),
        'trimestral': lambda d: d + relativedelta(months=3),
        'quadrimestral': lambda d: d + relativedelta(months=4),
        'semestral': lambda d: d + relativedelta(months=6),
        'anual': lambda d: d + relativedelta(years=1)
    }
    
    # Determinar quantas parcelas gerar
    if numero_parcelas == 'x':
        parcelas_a_gerar = 60  # Gerar 60 períodos para infinitas
    else:
        parcelas_a_gerar = int(numero_parcelas)
    
    # Gerar parcelas individuais (sem registro pai)
    data_atual = datetime.strptime(data_inicio, '%Y-%m-%d').date()
    if data_fim:
        data_limite = datetime.strptime(data_fim, '%Y-%m-%d').date()
    else:
        data_limite = None
    
    incremento_func = incrementos.get(tipo_recorrencia, incrementos['mensal'])
    parcelas_criadas = []
    
    for i in range(parcelas_a_gerar):
        # Se há data fim e passamos dela, parar
        if data_limite and data_atual > data_limite:
            break
            
        # Ajustar dia se especificado
        if dia_comum:
            try:
                data_atual = data_atual.replace(day=dia_comum)
            except ValueError:
                # Dia não existe no mês (ex: 31 em fevereiro)
                pass
        
        # Inserir parcela individual
        cursor = conn.execute('''
            INSERT INTO despesa (categoria_id, subcategoria_id, data_inicio, valor, tipo_recorrencia, numero_parcelas, parcela_atual, dia_comum_pagamento, usuario_id, fixo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (categoria_id, subcategoria_id, data_atual.strftime('%Y-%m-%d'), valor_parcela, tipo_recorrencia, numero_parcelas, i+1, dia_comum, user_id, fixo))
        
        parcelas_criadas.append(cursor.lastrowid)
        
        # Próximo período baseado no tipo de recorrência
        data_atual = incremento_func(data_atual)
    
    conn.commit()
    conn.close()
    return parcelas_criadas
