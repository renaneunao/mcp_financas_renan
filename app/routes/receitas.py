from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.database import get_db_connection, get_categorias_receitas, get_subcategorias_receitas, gerar_parcelas_receita
from app.routes.auth import login_required, get_current_user_id
from datetime import datetime

receitas_bp = Blueprint('receitas', __name__, url_prefix='/receitas')

@receitas_bp.route('/toggle-pagamento/<int:id>', methods=['POST'])
@login_required
def toggle_pagamento(id):
    """Alterna o status de pagamento de uma receita"""
    user_id = get_current_user_id()
    conn = get_db_connection()
    
    try:
        # Verificar se a receita pertence ao usuário
        receita = conn.execute(
            'SELECT pago FROM receita WHERE id = ? AND usuario_id = ?', 
            (id, user_id)
        ).fetchone()
        
        if not receita:
            return jsonify({'success': False, 'message': 'Receita não encontrada'}), 404
        
        # Alternar status
        novo_status = not receita['pago']
        conn.execute(
            'UPDATE receita SET pago = ? WHERE id = ? AND usuario_id = ?',
            (novo_status, id, user_id)
        )
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True, 
            'pago': novo_status,
            'message': 'Pagamento confirmado' if novo_status else 'Pagamento desmarcado'
        })
        
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'message': str(e)}), 500

@receitas_bp.route('/')
@login_required
def index():
    user_id = get_current_user_id()
    conn = get_db_connection()
    
    # Obter parâmetros de filtro
    categoria = request.args.get('categoria')
    subcategoria = request.args.get('subcategoria')
    mes = request.args.get('mes')
    ano = request.args.get('ano')
    
    # Construir query com filtros
    query = '''
        SELECT r.*, cr.nome as categoria_nome, sr.nome as subcategoria_nome
        FROM receita r
        JOIN categoria_receita cr ON r.categoria_id = cr.id
        LEFT JOIN subcategoria_receita sr ON r.subcategoria_id = sr.id
        WHERE r.usuario_id = ?
    '''
    
    params = [user_id]
    
    if categoria:
        query += " AND r.categoria_id = ?"
        params.append(categoria)
    
    if subcategoria:
        query += " AND r.subcategoria_id = ?"
        params.append(subcategoria)
    
    if mes:
        query += " AND strftime('%m', r.data_inicio) = ?"
        params.append(f"{int(mes):02d}")
    
    if ano:
        query += " AND strftime('%Y', r.data_inicio) = ?"
        params.append(str(ano))
    
    query += " ORDER BY r.data_inicio DESC"
    
    receitas = conn.execute(query, params).fetchall()
    
    # Converter Row objects para dicionários e converter datas
    receitas_formatadas = []
    total_valor = 0
    maior_valor = 0
    
    for receita in receitas:
        receita_dict = dict(receita)
        if receita_dict['data_inicio']:
            try:
                receita_dict['data_inicio'] = datetime.strptime(receita_dict['data_inicio'], '%Y-%m-%d')
            except:
                receita_dict['data_inicio'] = None
        if receita_dict.get('data_fim'):
            try:
                receita_dict['data_fim'] = datetime.strptime(receita_dict['data_fim'], '%Y-%m-%d')
            except:
                receita_dict['data_fim'] = None
        
        # Calcular estatísticas
        valor = float(receita_dict.get('valor', 0))
        total_valor += valor
        if valor > maior_valor:
            maior_valor = valor
            
        receitas_formatadas.append(type('obj', (object,), receita_dict))
    
    # Calcular média
    media_valor = total_valor / len(receitas_formatadas) if receitas_formatadas else 0
    
    # Obter categorias para o filtro
    categorias = get_categorias_receitas(usuario_id=user_id)
    
    # Preparar estatísticas
    estatisticas = {
        'total': len(receitas_formatadas),
        'valor_total': total_valor,
        'media_valor': media_valor,
        'maior_valor': maior_valor
    }
    
    conn.close()
    return render_template('receitas/index.html', receitas=receitas_formatadas, categorias=categorias, stats=estatisticas)

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
        valor_parcela = request.form['valor_parcela']
        fixo = bool(request.form.get('fixo'))  # Checkbox para receita fixa
        
        # Validações
        if not categoria_id or not data_inicio or not tipo_recorrencia or not valor_parcela:
            flash('Categoria, data de início, tipo de recorrência e valor por parcela são obrigatórios.', 'error')
            return redirect(url_for('receitas.nova'))
        
        try:
            # Converter valor: se tem vírgula, tratar como separador decimal brasileiro
            if ',' in valor_parcela:
                valor_parcela = valor_parcela.replace('.', '').replace(',', '.')
            valor_parcela = float(valor_parcela)
            if valor_parcela <= 0:
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
                tipo_recorrencia, valor_parcela, dia_comum_recebimento, user_id, fixo
            )
            flash('Receita cadastrada com sucesso!', 'success')
            return redirect(url_for('receitas.index'))
        except Exception as e:
            flash(f'Erro ao cadastrar receita: {str(e)}', 'error')
    
    categorias = get_categorias_receitas(usuario_id=user_id)
    
    # Para nova receita, carregar subcategorias da primeira categoria se existir
    subcategorias = []
    if categorias:
        primeira_categoria_id = categorias[0]['id']
        subcategorias = get_subcategorias_receitas(categoria_id=primeira_categoria_id, usuario_id=user_id)
    
    return render_template('receitas/form.html', categorias=categorias, subcategorias=subcategorias, receita=None)

@receitas_bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id):
    user_id = get_current_user_id()
    conn = get_db_connection()
    
    if request.method == 'POST':
        categoria_id = request.form['categoria_id']
        subcategoria_id = request.form.get('subcategoria_id') or None
        data_inicio = request.form['data_inicio']
        valor = request.form['valor']
        fixo = bool(request.form.get('fixo'))
        
        # Validações
        if not categoria_id or not data_inicio or not valor:
            flash('Categoria, data e valor são obrigatórios.', 'error')
            return redirect(url_for('receitas.editar', id=id))
        
        try:
            # Converter valor: se tem vírgula, tratar como separador decimal brasileiro
            if ',' in valor:
                valor = valor.replace('.', '').replace(',', '.')
            valor = float(valor)
            if valor <= 0:
                flash('O valor deve ser maior que zero.', 'error')
                return redirect(url_for('receitas.editar', id=id))
        except ValueError:
            flash('Valor inválido.', 'error')
            return redirect(url_for('receitas.editar', id=id))
        
        try:
            conn.execute('''
                UPDATE receita 
                SET categoria_id = ?, subcategoria_id = ?, data_inicio = ?, valor = ?, fixo = ?
                WHERE id = ?
            ''', (categoria_id, subcategoria_id, data_inicio, valor, fixo, id))
            conn.commit()
            flash('Receita atualizada com sucesso!', 'success')
            return redirect(url_for('receitas.index'))
        except Exception as e:
            flash(f'Erro ao atualizar receita: {str(e)}', 'error')
        finally:
            conn.close()
    
    # GET - carregar dados para edição
    receita = conn.execute('''
        SELECT r.*, cr.nome as categoria_nome, sr.nome as subcategoria_nome
        FROM receita r
        JOIN categoria_receita cr ON r.categoria_id = cr.id
        LEFT JOIN subcategoria_receita sr ON r.subcategoria_id = sr.id
        WHERE r.id = ?
    ''', (id,)).fetchone()
    
    if not receita:
        flash('Receita não encontrada.', 'error')
        conn.close()
        return redirect(url_for('receitas.index'))
    
    categorias = get_categorias_receitas(usuario_id=user_id)
    subcategorias = get_subcategorias_receitas(receita['categoria_id'], usuario_id=user_id)
    conn.close()
    
    return render_template('receitas/form.html', categorias=categorias, subcategorias=subcategorias, receita=receita)

@receitas_bp.route('/excluir/<int:id>', methods=['POST'])
@login_required
def excluir(id):
    conn = get_db_connection()
    try:
        # Excluir a receita individual
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
