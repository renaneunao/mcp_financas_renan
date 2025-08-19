from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.database import get_db_connection, get_categorias_despesas, get_subcategorias_despesas, gerar_parcelas_despesa
from app.routes.auth import login_required, get_current_user_id
from datetime import datetime

despesas_bp = Blueprint('despesas', __name__, url_prefix='/despesas')

@despesas_bp.route('/toggle-pagamento/<int:id>', methods=['POST'])
@login_required
def toggle_pagamento(id):
    """Alterna o status de pagamento de uma despesa"""
    user_id = get_current_user_id()
    conn = get_db_connection()
    
    try:
        # Verificar se a despesa pertence ao usuário
        despesa = conn.execute(
            'SELECT pago FROM despesa WHERE id = ? AND usuario_id = ?', 
            (id, user_id)
        ).fetchone()
        
        if not despesa:
            return jsonify({'success': False, 'message': 'Despesa não encontrada'}), 404
        
        # Alternar status
        novo_status = not despesa['pago']
        conn.execute(
            'UPDATE despesa SET pago = ? WHERE id = ? AND usuario_id = ?',
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

@despesas_bp.route('/')
@login_required
def index():
    user_id = get_current_user_id()
    conn = get_db_connection()
    
    # Obter parâmetros de filtro
    categoria = request.args.get('categoria')
    mes = request.args.get('mes')
    ano = request.args.get('ano')
    
    # Construir query com filtros
    query = '''
        SELECT d.*, cd.nome as categoria_nome, sd.nome as subcategoria_nome
        FROM despesa d
        JOIN categoria_despesa cd ON d.categoria_id = cd.id
        LEFT JOIN subcategoria_despesa sd ON d.subcategoria_id = sd.id
        WHERE d.usuario_id = ?
    '''
    
    params = [user_id]
    
    if categoria:
        query += " AND d.categoria_id = ?"
        params.append(categoria)
    
    if mes:
        query += " AND strftime('%m', d.data_inicio) = ?"
        params.append(f"{int(mes):02d}")
    
    if ano:
        query += " AND strftime('%Y', d.data_inicio) = ?"
        params.append(str(ano))
    
    query += " ORDER BY d.data_inicio DESC"
    
    despesas = conn.execute(query, params).fetchall()
    
    # Converter Row objects para dicionários e converter datas
    despesas_formatadas = []
    total_valor = 0
    maior_valor = 0
    
    for despesa in despesas:
        despesa_dict = dict(despesa)
        if despesa_dict['data_inicio']:
            try:
                despesa_dict['data_inicio'] = datetime.strptime(despesa_dict['data_inicio'], '%Y-%m-%d')
            except:
                despesa_dict['data_inicio'] = None
        if despesa_dict.get('data_fim'):
            try:
                despesa_dict['data_fim'] = datetime.strptime(despesa_dict['data_fim'], '%Y-%m-%d')
            except:
                despesa_dict['data_fim'] = None
        
        # Calcular estatísticas
        valor = float(despesa_dict.get('valor', 0))
        total_valor += valor
        if valor > maior_valor:
            maior_valor = valor
            
        despesas_formatadas.append(type('obj', (object,), despesa_dict))
    
    # Calcular média
    media_valor = total_valor / len(despesas_formatadas) if despesas_formatadas else 0
    
    # Obter categorias para o filtro
    categorias = get_categorias_despesas(usuario_id=user_id)
    
    # Preparar estatísticas
    estatisticas = {
        'total': len(despesas_formatadas),
        'valor_total': total_valor,
        'media_valor': media_valor,
        'maior_valor': maior_valor
    }
    
    conn.close()
    return render_template('despesas/index.html', despesas=despesas_formatadas, categorias=categorias, stats=estatisticas)

@despesas_bp.route('/nova', methods=['GET', 'POST'])
@login_required
def nova():
    user_id = get_current_user_id()
    if request.method == 'POST':
        categoria_id = request.form['categoria_id']
        subcategoria_id = request.form.get('subcategoria_id') or None
        data_inicio = request.form['data_inicio']
        data_fim = request.form.get('data_fim') or None
        tipo_recorrencia = request.form['tipo_recorrencia']
        dia_comum = request.form.get('dia_comum_pagamento')
        valor_parcela = request.form['valor_parcela']
        fixo = bool(request.form.get('fixo'))  # Checkbox para despesa fixa
        
        # Validações
        if not categoria_id or not data_inicio or not tipo_recorrencia or not valor_parcela:
            flash('Categoria, data de início, tipo de recorrência e valor por parcela são obrigatórios.', 'error')
            return redirect(url_for('despesas.nova'))
        
        try:
            # Converter valor: se tem vírgula, tratar como separador decimal brasileiro
            if ',' in valor_parcela:
                valor_parcela = valor_parcela.replace('.', '').replace(',', '.')
            valor_parcela = float(valor_parcela)
            if valor_parcela <= 0:
                flash('O valor deve ser maior que zero.', 'error')
                return redirect(url_for('despesas.nova'))
        except ValueError:
            flash('Valor inválido.', 'error')
            return redirect(url_for('despesas.nova'))
        
        # Converter dia comum para inteiro se fornecido
        if dia_comum:
            try:
                dia_comum = int(dia_comum)
                if dia_comum < 1 or dia_comum > 31:
                    flash('Dia comum deve estar entre 1 e 31.', 'error')
                    return redirect(url_for('despesas.nova'))
            except ValueError:
                dia_comum = None
        else:
            dia_comum = None
        
        # Gerar parcelas
        try:
            despesa_pai_id = gerar_parcelas_despesa(
                categoria_id, subcategoria_id, data_inicio, data_fim, 
                tipo_recorrencia, valor_parcela, dia_comum, user_id, fixo
            )
            flash('Despesa cadastrada com sucesso!', 'success')
            return redirect(url_for('despesas.index'))
        except Exception as e:
            flash(f'Erro ao cadastrar despesa: {str(e)}', 'error')
    
    categorias = get_categorias_despesas(usuario_id=user_id)
    
    # Para nova despesa, carregar subcategorias da primeira categoria se existir
    subcategorias = []
    if categorias:
        primeira_categoria_id = categorias[0]['id']
        subcategorias = get_subcategorias_despesas(categoria_id=primeira_categoria_id, usuario_id=user_id)
    
    return render_template('despesas/form.html', categorias=categorias, subcategorias=subcategorias, despesa=None)

@despesas_bp.route('/editar/<int:id>', methods=['GET', 'POST'])
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
            return redirect(url_for('despesas.editar', id=id))
        
        try:
            # Converter valor: se tem vírgula, tratar como separador decimal brasileiro
            if ',' in valor:
                valor = valor.replace('.', '').replace(',', '.')
            valor = float(valor)
            if valor <= 0:
                flash('O valor deve ser maior que zero.', 'error')
                return redirect(url_for('despesas.editar', id=id))
        except ValueError:
            flash('Valor inválido.', 'error')
            return redirect(url_for('despesas.editar', id=id))
        
        try:
            conn.execute('''
                UPDATE despesa 
                SET categoria_id = ?, subcategoria_id = ?, data_inicio = ?, valor = ?, fixo = ?
                WHERE id = ?
            ''', (categoria_id, subcategoria_id, data_inicio, valor, fixo, id))
            conn.commit()
            flash('Despesa atualizada com sucesso!', 'success')
            return redirect(url_for('despesas.index'))
        except Exception as e:
            flash(f'Erro ao atualizar despesa: {str(e)}', 'error')
        finally:
            conn.close()
    
    # GET - carregar dados para edição
    despesa = conn.execute('''
        SELECT d.*, cd.nome as categoria_nome, sd.nome as subcategoria_nome
        FROM despesa d
        JOIN categoria_despesa cd ON d.categoria_id = cd.id
        LEFT JOIN subcategoria_despesa sd ON d.subcategoria_id = sd.id
        WHERE d.id = ?
    ''', (id,)).fetchone()
    
    if not despesa:
        flash('Despesa não encontrada.', 'error')
        conn.close()
        return redirect(url_for('despesas.index'))
    
    categorias = get_categorias_despesas(usuario_id=user_id)
    subcategorias = get_subcategorias_despesas(despesa['categoria_id'], usuario_id=user_id)
    conn.close()
    
    return render_template('despesas/form.html', categorias=categorias, subcategorias=subcategorias, despesa=despesa)

@despesas_bp.route('/excluir/<int:id>', methods=['POST'])
@login_required
def excluir(id):
    conn = get_db_connection()
    try:
        # Excluir a despesa individual
        conn.execute('DELETE FROM despesa WHERE id = ?', (id,))
        conn.commit()
        flash('Despesa excluída com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao excluir despesa: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('despesas.index'))

@despesas_bp.route('/subcategorias/<int:categoria_id>')
@login_required
def subcategorias(categoria_id):
    user_id = get_current_user_id()
    subcategorias = get_subcategorias_despesas(categoria_id, usuario_id=user_id)
    return jsonify([{'id': sub['id'], 'nome': sub['nome']} for sub in subcategorias])
