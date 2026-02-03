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
    cartoes = conn.execute('''
        SELECT c.*, i.nome as instituicao_nome, i.codigo as instituicao_codigo
        FROM cartao_credito c
        JOIN instituicao_financeira i ON c.instituicao_id = i.id
        WHERE c.usuario_id = ? AND c.ativo = 1
        ORDER BY c.created_at DESC
    ''', (user_id,)).fetchall()
    
    # Buscar instituições financeiras ativas
    instituicoes = conn.execute('''
        SELECT * FROM instituicao_financeira
        WHERE ativo = 1
        ORDER BY nome
    ''').fetchall()
    
    conn.close()
    
    return render_template('cartoes/index.html', 
                         cartoes=cartoes,
                         instituicoes=instituicoes)

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
