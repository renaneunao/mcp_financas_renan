import sqlite3
import os
from datetime import datetime

# Define o caminho do banco de dados
# Usa DB_PATH se existir, senão usa 'financas.db' no diretório atual
DATABASE = os.environ.get('DB_PATH', 'financas.db')

# Garante que o diretório do banco de dados existe
db_dir = os.path.dirname(os.path.abspath(DATABASE))
if db_dir and not os.path.exists(db_dir):
    os.makedirs(db_dir, exist_ok=True)

def get_db_connection():
    """Conecta ao banco de dados SQLite"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

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

def get_cartoes_credito(usuario_id):
    """Retorna todos os cartões de crédito do usuário"""
    conn = get_db_connection()
    cartoes = conn.execute('''
        SELECT c.*, i.nome as instituicao_nome 
        FROM cartao_credito c
        JOIN instituicao_financeira i ON c.instituicao_id = i.id
        WHERE c.usuario_id = ? AND c.ativo = 1
        ORDER BY c.created_at DESC
    ''', (usuario_id,)).fetchall()
    conn.close()
    return cartoes

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
        # Gerar até o final do ano subsequente (ano atual + 1)
        dt_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        ano_limite = dt_inicio.year + 1
        dt_limite = datetime(ano_limite, 12, 31).date()
        
        # Contagem precisa
        count = 0
        tmp = dt_inicio
        inc = incrementos.get(tipo_recorrencia, incrementos['mensal'])
        
        while tmp <= dt_limite:
            count += 1
            tmp = inc(tmp)
            
        parcelas_a_gerar = count if count > 0 else 1
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

def gerar_parcelas_despesa(categoria_id, subcategoria_id, data_inicio, data_fim, tipo_recorrencia, valor_parcela, dia_comum, user_id, fixo=False, cartao_id=None):
    """Gera parcelas individuais para uma despesa"""
    from datetime import datetime
    from dateutil.relativedelta import relativedelta
    
    conn = get_db_connection()
    
    # Se for tipo único, inserir apenas um registro
    if tipo_recorrencia == 'unica':
        cursor = conn.execute('''
            INSERT INTO despesa (categoria_id, subcategoria_id, data_inicio, valor, tipo_recorrencia, numero_parcelas, parcela_atual, usuario_id, fixo, cartao_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (categoria_id, subcategoria_id, data_inicio, valor_parcela, 'unica', '1', 1, user_id, fixo, cartao_id))
        
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
        # Gerar até o final do ano subsequente (ano atual + 1)
        dt_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        ano_limite = dt_inicio.year + 1
        dt_limite = datetime(ano_limite, 12, 31).date()
        
        # Contagem precisa
        count = 0
        tmp = dt_inicio
        inc = incrementos.get(tipo_recorrencia, incrementos['mensal'])
        
        while tmp <= dt_limite:
            count += 1
            tmp = inc(tmp)
            
        parcelas_a_gerar = count if count > 0 else 1
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
            INSERT INTO despesa (categoria_id, subcategoria_id, data_inicio, valor, tipo_recorrencia, numero_parcelas, parcela_atual, dia_comum_pagamento, usuario_id, fixo, cartao_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (categoria_id, subcategoria_id, data_atual.strftime('%Y-%m-%d'), valor_parcela, tipo_recorrencia, numero_parcelas, i+1, dia_comum, user_id, fixo, cartao_id))
        
        parcelas_criadas.append(cursor.lastrowid)
        
        # Próximo período baseado no tipo de recorrência
        data_atual = incremento_func(data_atual)
    
    conn.commit()
    conn.close()
    return parcelas_criadas
