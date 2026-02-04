from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.database import get_db_connection
from app.routes.auth import login_required, get_current_user_id

cartoes_bp = Blueprint('cartoes', __name__, url_prefix='/cartoes')

@cartoes_bp.route('/')
@login_required
def index():
    """Página principal de gerenciamento de cartões"""
    user_id = get_current_user_id()
    conn = get_db_connection()
    
    # Buscar cartões do usuário
    cartoes_list = conn.execute('''
        SELECT c.*, i.nome as instituicao_nome, i.codigo as instituicao_codigo
        FROM cartao_credito c
        JOIN instituicao_financeira i ON c.instituicao_id = i.id
        WHERE c.usuario_id = ? AND c.ativo = 1
        ORDER BY i.nome, c.nome_cartao
    ''', (user_id,)).fetchall()

    # Agrupar cartões por Instituição
    cartoes_agrupados = {}
    for c in cartoes_list:
        inst = c['instituicao_nome']
        if inst not in cartoes_agrupados:
            cartoes_agrupados[inst] = []
        cartoes_agrupados[inst].append(c)
    
    # Buscar instituições financeiras ativas
    instituicoes = conn.execute('''
        SELECT * FROM instituicao_financeira
        WHERE ativo = 1
        ORDER BY nome
    ''').fetchall()

    # Filtros de Mês e Ano (Default: Atual)
    from datetime import datetime
    hoje = datetime.now()
    mes_selecionado = request.args.get('mes', str(hoje.month))
    ano_selecionado = request.args.get('ano', str(hoje.year))
    filtro_vencimento = f"{ano_selecionado}-{int(mes_selecionado):02d}"

    # Buscar TODAS as despesas de cartão para montar a hierarquia
    despesas_raw = conn.execute('''
        SELECT 
            d.*,
            c.nome_cartao,
            c.dia_vencimento,
            i.nome as nome_banco,
            i.id as instituicao_id,
            cat.nome as categoria_nome,
            sub.nome as subcategoria_nome,
            strftime('%Y-%m', d.data_inicio) as mes_compra,
            CASE 
                WHEN strftime('%d', d.data_inicio) > c.dia_fechamento THEN strftime('%Y-%m', date(d.data_inicio, '+1 month'))
                ELSE strftime('%Y-%m', d.data_inicio)
            END as mes_vencimento
        FROM despesa d
        JOIN cartao_credito c ON d.cartao_id = c.id
        JOIN instituicao_financeira i ON c.instituicao_id = i.id
        JOIN categoria_despesa cat ON d.categoria_id = cat.id
        LEFT JOIN subcategoria_despesa sub ON d.subcategoria_id = sub.id
        WHERE d.usuario_id = ?
        ORDER BY mes_vencimento DESC, d.data_inicio DESC
    ''', (user_id,)).fetchall()

    faturas_view = {}
    gastos_por_cartao_id = {}
    
    for row in despesas_raw:
        if row['mes_vencimento'] != filtro_vencimento:
            continue

        banco = row['nome_banco']
        cartao = row['nome_cartao']
        valor = row['valor']
        cid = row['cartao_id']
        
        # Somar gastos por ID de cartão
        gastos_por_cartao_id[cid] = gastos_por_cartao_id.get(cid, 0.0) + valor
        
        # Construir descrição faturas
        descricao = row['categoria_nome']
        if row['subcategoria_nome']:
            descricao += f" - {row['subcategoria_nome']}"
        
        if banco not in faturas_view:
            faturas_view[banco] = {
                'valor_total': 0.0,
                'dia_vencimento': row['dia_vencimento'],
                'cartoes': {}
            }
            
        faturas_view[banco]['valor_total'] += valor
        
        if cartao not in faturas_view[banco]['cartoes']:
            faturas_view[banco]['cartoes'][cartao] = {
                'valor_total': 0.0,
                'itens': []
            }
            
        faturas_view[banco]['cartoes'][cartao]['valor_total'] += valor
        
        faturas_view[banco]['cartoes'][cartao]['itens'].append({
            'descricao': descricao,
            'valor': valor,
            'data': row['data_inicio'],
            'parcela_atual': row['parcela_atual'],
            'numero_parcelas': row['numero_parcelas'],
            'id': row['id']
        })

    # Calcular total bloqueado (consumo total do limite)
    # Lógica: 
    # 1. Compras Parceladas: Somar TODAS as parcelas que ainda não foram pagas.
    # 2. Assinaturas/Fixos/Recorrentes: Apenas o valor do mês selecionado consome o limite (pois são renovadas mensalmente).
    bloqueado_por_cartao_id = {}
    
    # Primeiro: Gastos de compras parceladas (todas as parcelas não pagas e não fixas)
    bloqueado_parcelado = conn.execute('''
        SELECT cartao_id, SUM(valor) as total
        FROM despesa
        WHERE usuario_id = ? AND pago = 0 AND cartao_id IS NOT NULL
        AND (numero_parcelas != '1' AND numero_parcelas != 'x')
        AND fixo = 0
        GROUP BY cartao_id
    ''', (user_id,)).fetchall()
    
    # Segundo: Gastos recorrentes, fixos ou de parcela única no mês selecionado
    bloqueado_recorrente = conn.execute('''
        SELECT cartao_id, SUM(valor) as total
        FROM (
            SELECT d.cartao_id, d.valor,
            CASE 
                WHEN strftime('%d', d.data_inicio) > c.dia_fechamento THEN strftime('%Y-%m', date(d.data_inicio, '+1 month'))
                ELSE strftime('%Y-%m', d.data_inicio)
            END as mes_vencimento
            FROM despesa d
            JOIN cartao_credito c ON d.cartao_id = c.id
            WHERE d.usuario_id = ? AND d.pago = 0 AND d.cartao_id IS NOT NULL
            AND (d.numero_parcelas = '1' OR d.numero_parcelas = 'x' OR d.fixo = 1)
        )
        WHERE mes_vencimento = ?
        GROUP BY cartao_id
    ''', (user_id, filtro_vencimento)).fetchall()

    for row in bloqueado_parcelado:
        bloqueado_por_cartao_id[row['cartao_id']] = row['total']
    
    for row in bloqueado_recorrente:
        bloqueado_por_cartao_id[row['cartao_id']] = bloqueado_por_cartao_id.get(row['cartao_id'], 0.0) + row['total']

    # Agrupar cartões por Instituição e adicionar valores calculados
    cartoes_agrupados = {}
    for c in cartoes_list:
        inst = c['instituicao_nome']
        if inst not in cartoes_agrupados:
            cartoes_agrupados[inst] = []
        
        # Criar dicionário do cartão e injetar valores
        c_dict = dict(c)
        c_dict['valor_fatura_atual'] = gastos_por_cartao_id.get(c['id'], 0.0)
        c_dict['valor_bloqueado'] = bloqueado_por_cartao_id.get(c['id'], 0.0)
        c_dict['valor_disponivel'] = max(0.0, c_dict['limite_total'] - c_dict['valor_bloqueado'])
        
        cartoes_agrupados[inst].append(c_dict)
    
    conn.close()
    
    return render_template('cartoes/index.html', 
                         cartoes=cartoes_agrupados,
                         instituicoes=instituicoes,
                         faturas=faturas_view,
                         mes_selecionado=int(mes_selecionado),
                         ano_selecionado=int(ano_selecionado))

@cartoes_bp.route('/detalhes/<int:cartao_id>')
@login_required
def detalhes(cartao_id):
    """Retorna todas as despesas de um cartão específico para exibir no modal"""
    user_id = get_current_user_id()
    conn = get_db_connection()
    
    # Buscar informações do cartão
    cartao_row = conn.execute('''
        SELECT c.*, i.nome as instituicao_nome
        FROM cartao_credito c
        JOIN instituicao_financeira i ON c.instituicao_id = i.id
        WHERE c.id = ? AND c.usuario_id = ?
    ''', (cartao_id, user_id)).fetchone()
    
    if not cartao_row:
        conn.close()
        return jsonify({'success': False, 'message': 'Cartão não encontrado'}), 404
        
    # Recalcular estatísticas para este cartão específico (mesma lógica do index)
    from datetime import datetime
    hoje = datetime.now()
    filtro_vencimento = f"{hoje.year}-{int(hoje.month):02d}"

    # 1. Compras Parceladas Reais (Não fixas)
    bloqueado_parcelado = conn.execute('''
        SELECT SUM(valor) as total FROM despesa
        WHERE usuario_id = ? AND cartao_id = ? AND pago = 0
        AND (numero_parcelas != '1' AND numero_parcelas != 'x')
        AND fixo = 0
    ''', (user_id, cartao_id)).fetchone()['total'] or 0.0

    # 2. Assinaturas e Fixos (Apenas Mês Atual)
    bloqueado_recorrente = conn.execute('''
        SELECT SUM(valor) as total FROM (
            SELECT d.valor,
            CASE 
                WHEN strftime('%d', d.data_inicio) > c.dia_fechamento THEN strftime('%Y-%m', date(d.data_inicio, '+1 month'))
                ELSE strftime('%Y-%m', d.data_inicio)
            END as mes_vencimento
            FROM despesa d
            JOIN cartao_credito c ON d.cartao_id = c.id
            WHERE d.usuario_id = ? AND d.cartao_id = ? AND d.pago = 0
            AND (d.numero_parcelas = '1' OR d.numero_parcelas = 'x' OR d.fixo = 1)
        ) WHERE mes_vencimento = ?
    ''', (user_id, cartao_id, filtro_vencimento)).fetchone()['total'] or 0.0

    valor_bloqueado = bloqueado_parcelado + bloqueado_recorrente
    cartao_dict = dict(cartao_row)
    cartao_dict['valor_bloqueado'] = valor_bloqueado
    cartao_dict['valor_disponivel'] = max(0.0, cartao_dict['limite_total'] - valor_bloqueado)

    # Buscar despesas
    despesas = conn.execute('''
        SELECT d.*, cat.nome as categoria_nome, sub.nome as subcategoria_nome
        FROM despesa d
        JOIN categoria_despesa cat ON d.categoria_id = cat.id
        LEFT JOIN subcategoria_despesa sub ON d.subcategoria_id = sub.id
        WHERE d.cartao_id = ? AND d.usuario_id = ?
        ORDER BY d.data_inicio DESC
    ''', (cartao_id, user_id)).fetchall()
    
    conn.close()
    
    return jsonify({
        'success': True,
        'cartao': cartao_dict,
        'despesas': [dict(d) for d in despesas]
    })

@cartoes_bp.route('/adicionar', methods=['POST'])
@login_required
def adicionar():
    """Adiciona um novo cartão de crédito"""
    user_id = get_current_user_id()
    
    instituicao_id = request.form.get('instituicao_id')
    nome_cartao = request.form.get('nome_cartao')
    ultimos_digitos = request.form.get('ultimos_digitos')
    limite_total = request.form.get('limite_total', 0)
    dia_vencimento = request.form.get('dia_vencimento')
    dia_fechamento = request.form.get('dia_fechamento')
    
    # Validações
    if not all([instituicao_id, nome_cartao, ultimos_digitos, dia_vencimento, dia_fechamento]):
        flash('Todos os campos são obrigatórios', 'error')
        return redirect(url_for('cartoes.index'))
    
    if len(ultimos_digitos) != 4 or not ultimos_digitos.isdigit():
        flash('Os últimos dígitos devem conter exatamente 4 números', 'error')
        return redirect(url_for('cartoes.index'))
    
    try:
        dia_vencimento = int(dia_vencimento)
        dia_fechamento = int(dia_fechamento)
        limite_total = float(limite_total)
        
        if not (1 <= dia_vencimento <= 31) or not (1 <= dia_fechamento <= 31):
            flash('Dias de vencimento e fechamento devem estar entre 1 e 31', 'error')
            return redirect(url_for('cartoes.index'))
            
    except ValueError:
        flash('Valores inválidos fornecidos', 'error')
        return redirect(url_for('cartoes.index'))
    
    conn = get_db_connection()
    
    try:
        conn.execute('''
            INSERT INTO cartao_credito 
            (usuario_id, instituicao_id, nome_cartao, ultimos_digitos, 
             limite_total, dia_vencimento, dia_fechamento)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, instituicao_id, nome_cartao, ultimos_digitos, 
              limite_total, dia_vencimento, dia_fechamento))
        
        conn.commit()
        flash('Cartão adicionado com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao adicionar cartão: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('cartoes.index'))

@cartoes_bp.route('/editar/<int:cartao_id>', methods=['POST'])
@login_required
def editar(cartao_id):
    """Edita um cartão de crédito existente"""
    user_id = get_current_user_id()
    
    instituicao_id = request.form.get('instituicao_id')
    nome_cartao = request.form.get('nome_cartao')
    ultimos_digitos = request.form.get('ultimos_digitos')
    limite_total = request.form.get('limite_total', 0)
    dia_vencimento = request.form.get('dia_vencimento')
    dia_fechamento = request.form.get('dia_fechamento')
    
    # Validações
    if not all([instituicao_id, nome_cartao, ultimos_digitos, dia_vencimento, dia_fechamento]):
        flash('Todos os campos são obrigatórios', 'error')
        return redirect(url_for('cartoes.index'))
    
    if len(ultimos_digitos) != 4 or not ultimos_digitos.isdigit():
        flash('Os últimos dígitos devem conter exatamente 4 números', 'error')
        return redirect(url_for('cartoes.index'))
    
    try:
        dia_vencimento = int(dia_vencimento)
        dia_fechamento = int(dia_fechamento)
        limite_total = float(limite_total)
        
        if not (1 <= dia_vencimento <= 31) or not (1 <= dia_fechamento <= 31):
            flash('Dias de vencimento e fechamento devem estar entre 1 e 31', 'error')
            return redirect(url_for('cartoes.index'))
            
    except ValueError:
        flash('Valores inválidos fornecidos', 'error')
        return redirect(url_for('cartoes.index'))
    
    conn = get_db_connection()
    
    try:
        # Verificar se o cartão pertence ao usuário
        cartao = conn.execute('''
            SELECT id FROM cartao_credito 
            WHERE id = ? AND usuario_id = ?
        ''', (cartao_id, user_id)).fetchone()
        
        if not cartao:
            flash('Cartão não encontrado', 'error')
            return redirect(url_for('cartoes.index'))
        
        conn.execute('''
            UPDATE cartao_credito 
            SET instituicao_id = ?, nome_cartao = ?, ultimos_digitos = ?,
                limite_total = ?, dia_vencimento = ?, dia_fechamento = ?
            WHERE id = ? AND usuario_id = ?
        ''', (instituicao_id, nome_cartao, ultimos_digitos, limite_total,
              dia_vencimento, dia_fechamento, cartao_id, user_id))
        
        conn.commit()
        flash('Cartão atualizado com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao atualizar cartão: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('cartoes.index'))

@cartoes_bp.route('/excluir/<int:cartao_id>', methods=['POST'])
@login_required
def excluir(cartao_id):
    """Desativa um cartão de crédito (soft delete)"""
    user_id = get_current_user_id()
    
    conn = get_db_connection()
    
    try:
        # Verificar se o cartão pertence ao usuário
        cartao = conn.execute('''
            SELECT id FROM cartao_credito 
            WHERE id = ? AND usuario_id = ?
        ''', (cartao_id, user_id)).fetchone()
        
        if not cartao:
            flash('Cartão não encontrado', 'error')
            return redirect(url_for('cartoes.index'))
        
        # Soft delete - apenas marca como inativo
        conn.execute('''
            UPDATE cartao_credito 
            SET ativo = 0
            WHERE id = ? AND usuario_id = ?
        ''', (cartao_id, user_id))
        
        conn.commit()
        flash('Cartão removido com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao remover cartão: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('cartoes.index'))
