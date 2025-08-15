from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.database import get_db_connection, get_categorias_receitas, get_subcategorias_receitas, gerar_parcelas_receita
from app.routes.auth import login_required, get_current_user_id
from datetime import datetime

receitas_bp = Blueprint('receitas', __name__, url_prefix='/receitas')

@receitas_bp.route('/')
@login_required
def index():
    user_id = get_current_user_id()
    conn = get_db_connection()
    # Buscar apenas receitas pai (não são parcelas)
    receitas = conn.execute('''
        SELECT r.*, cr.nome as categoria_nome, sr.nome as subcategoria_nome
        FROM receita r
        JOIN categoria_receita cr ON r.categoria_id = cr.id
        LEFT JOIN subcategoria_receita sr ON r.subcategoria_id = sr.id
        WHERE r.receita_pai_id IS NULL AND r.usuario_id = ?
        ORDER BY r.data_inicio DESC
    ''', (user_id,)).fetchall()
    conn.close()
    return render_template('receitas/index.html', receitas=receitas)

@receitas_bp.route('/nova', methods=['GET', 'POST'])
@login_required
def nova():
    user_id = get_current_user_id()
    if request.method == 'POST':
        categoria_id = request.form['categoria_id']
        subcategoria_id = request.form.get('subcategoria_id') or None
        data_inicio = request.form['data_inicio']
        data_fim = request.form.get('data_fim') or None
        tipo_recorrencia = request.form['tipo_recorrencia']
        dia_comum_recebimento = request.form.get('dia_comum_recebimento') or None
        valor_total = request.form['valor_total']
        
        # Validações
        if not categoria_id or not data_inicio or not tipo_recorrencia or not valor_total:
            flash('Categoria, data de início, tipo de recorrência e valor são obrigatórios.', 'error')
            return redirect(url_for('receitas.nova'))
        
        try:
            valor_total = float(valor_total.replace(',', '.').replace('.', '', valor_total.count('.') - 1 if ',' in valor_total else valor_total.count('.') - 1))
            if valor_total <= 0:
                flash('O valor deve ser maior que zero.', 'error')
                return redirect(url_for('receitas.nova'))
        except ValueError:
            flash('Valor inválido.', 'error')
            return redirect(url_for('receitas.nova'))
        
        # Converter dia comum para inteiro se fornecido
        if dia_comum_recebimento:
            try:
                dia_comum_recebimento = int(dia_comum_recebimento)
                if dia_comum_recebimento < 1 or dia_comum_recebimento > 31:
                    flash('Dia comum deve estar entre 1 e 31.', 'error')
                    return redirect(url_for('receitas.nova'))
            except ValueError:
                dia_comum_recebimento = None
        else:
            dia_comum_recebimento = None
        
        # Gerar parcelas
        try:
            receita_pai_id = gerar_parcelas_receita(
                categoria_id, subcategoria_id, data_inicio, data_fim, 
                tipo_recorrencia, valor_total, dia_comum_recebimento, user_id
            )
            flash('Receita cadastrada com sucesso!', 'success')
            return redirect(url_for('receitas.index'))
        except Exception as e:
            flash(f'Erro ao cadastrar receita: {str(e)}', 'error')
    
    categorias = get_categorias_receitas(usuario_id=user_id)
    return render_template('receitas/form.html', categorias=categorias, receita=None)

@receitas_bp.route('/ver_parcelas/<int:receita_pai_id>')
def ver_parcelas(receita_pai_id):
    conn = get_db_connection()
    
    # Buscar receita pai
    receita_pai = conn.execute('''
        SELECT r.*, cr.nome as categoria_nome, sr.nome as subcategoria_nome
        FROM receita r
        JOIN categoria_receita cr ON r.categoria_id = cr.id
        LEFT JOIN subcategoria_receita sr ON r.subcategoria_id = sr.id
        WHERE r.id = ?
    ''', (receita_pai_id,)).fetchone()
    
    if not receita_pai:
        flash('Receita não encontrada.', 'error')
        return redirect(url_for('receitas.index'))
    
    # Buscar parcelas
    parcelas = conn.execute('''
        SELECT r.*, cr.nome as categoria_nome, sr.nome as subcategoria_nome
        FROM receita r
        JOIN categoria_receita cr ON r.categoria_id = cr.id
        LEFT JOIN subcategoria_receita sr ON r.subcategoria_id = sr.id
        WHERE r.receita_pai_id = ?
        ORDER BY r.parcela_atual
    ''', (receita_pai_id,)).fetchall()
    
    conn.close()
    return render_template('receitas/parcelas.html', receita_pai=receita_pai, parcelas=parcelas)

@receitas_bp.route('/excluir/<int:id>', methods=['POST'])
def excluir(id):
    conn = get_db_connection()
    try:
        # Verificar se é receita pai e excluir parcelas também
        parcelas = conn.execute('SELECT id FROM receita WHERE receita_pai_id = ?', (id,)).fetchall()
        for parcela in parcelas:
            conn.execute('DELETE FROM receita WHERE id = ?', (parcela['id'],))
        
        # Excluir a receita principal
        conn.execute('DELETE FROM receita WHERE id = ?', (id,))
        conn.commit()
        flash('Receita excluída com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao excluir receita: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('receitas.index'))

@receitas_bp.route('/subcategorias/<int:categoria_id>')
@login_required
def subcategorias(categoria_id):
    user_id = get_current_user_id()
    subcategorias = get_subcategorias_receitas(categoria_id, usuario_id=user_id)
    return jsonify([{'id': sub['id'], 'nome': sub['nome']} for sub in subcategorias])
