from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.database import get_db_connection, get_categorias_receitas, get_categorias_despesas, get_subcategorias_receitas, get_subcategorias_despesas
from app.routes.auth import login_required, get_current_user_id

categorias_bp = Blueprint('categorias', __name__, url_prefix='/categorias')

# Rotas para Categorias de Receitas
@categorias_bp.route('/receitas')
@login_required
def categorias_receitas():
    user_id = get_current_user_id()
    categorias = get_categorias_receitas(usuario_id=user_id)
    subcategorias = get_subcategorias_receitas(usuario_id=user_id)
    return render_template('categorias/receitas.html', categorias=categorias, subcategorias=subcategorias)

@categorias_bp.route('/receitas/nova', methods=['GET', 'POST'])
@login_required
def nova_categoria_receita():
    if request.method == 'POST':
        nome = request.form['nome']
        descricao = request.form.get('descricao', '')
        user_id = get_current_user_id()
        
        if not nome:
            flash('O nome da categoria é obrigatório.', 'error')
            return redirect(url_for('categorias.nova_categoria_receita'))
        
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO categoria_receita (nome, descricao, usuario_id) VALUES (?, ?, ?)', (nome, descricao, user_id))
            conn.commit()
            flash('Categoria de receita criada com sucesso!', 'success')
            return redirect(url_for('categorias.categorias_receitas'))
        except Exception as e:
            if 'UNIQUE constraint failed' in str(e):
                flash('Você já possui uma categoria com este nome.', 'error')
            else:
                flash(f'Erro ao criar categoria: {str(e)}', 'error')
        finally:
            conn.close()
    
    return render_template('categorias/form_categoria_receita.html', categoria=None)

@categorias_bp.route('/receitas/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_categoria_receita(id):
    user_id = get_current_user_id()
    conn = get_db_connection()
    categoria = conn.execute('SELECT * FROM categoria_receita WHERE id = ? AND usuario_id = ?', (id, user_id)).fetchone()
    
    if not categoria:
        flash('Categoria não encontrada.', 'error')
        return redirect(url_for('categorias.categorias_receitas'))
    
    if request.method == 'POST':
        nome = request.form['nome']
        descricao = request.form.get('descricao', '')
        
        if not nome:
            flash('O nome da categoria é obrigatório.', 'error')
            return redirect(url_for('categorias.editar_categoria_receita', id=id))
        
        try:
            conn.execute('UPDATE categoria_receita SET nome = ?, descricao = ? WHERE id = ? AND usuario_id = ?', (nome, descricao, id, user_id))
            conn.commit()
            flash('Categoria atualizada com sucesso!', 'success')
            return redirect(url_for('categorias.categorias_receitas'))
        except Exception as e:
            flash(f'Erro ao atualizar categoria: {str(e)}', 'error')
        finally:
            conn.close()
    
    conn.close()
    return render_template('categorias/form_categoria_receita.html', categoria=categoria)

@categorias_bp.route('/receitas/<int:id>/excluir', methods=['POST'])
@login_required
def excluir_categoria_receita(id):
    user_id = get_current_user_id()
    conn = get_db_connection()
    try:
        # Verificar se a categoria pertence ao usuário
        categoria = conn.execute('SELECT * FROM categoria_receita WHERE id = ? AND usuario_id = ?', (id, user_id)).fetchone()
        if not categoria:
            flash('Categoria não encontrada.', 'error')
            return redirect(url_for('categorias.categorias_receitas'))
        
        # Verificar se há receitas usando esta categoria
        receitas = conn.execute('SELECT COUNT(*) FROM receita WHERE categoria_id = ? AND usuario_id = ?', (id, user_id)).fetchone()[0]
        if receitas > 0:
            flash(f'Não é possível excluir esta categoria pois ela possui {receitas} receita(s) associada(s).', 'error')
            return redirect(url_for('categorias.categorias_receitas'))
        
        # Excluir subcategorias primeiro
        conn.execute('DELETE FROM subcategoria_receita WHERE categoria_id = ? AND usuario_id = ?', (id, user_id))
        # Excluir categoria
        conn.execute('DELETE FROM categoria_receita WHERE id = ? AND usuario_id = ?', (id, user_id))
        conn.commit()
        flash('Categoria e suas subcategorias excluídas com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao excluir categoria: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('categorias.categorias_receitas'))

@categorias_bp.route('/receitas/subcategoria/<int:id>/excluir', methods=['POST'])
@login_required
def excluir_subcategoria_receita(id):
    user_id = get_current_user_id()
    conn = get_db_connection()
    try:
        # Verificar se a subcategoria pertence ao usuário
        subcategoria = conn.execute('SELECT * FROM subcategoria_receita WHERE id = ? AND usuario_id = ?', (id, user_id)).fetchone()
        if not subcategoria:
            flash('Subcategoria não encontrada.', 'error')
            return redirect(url_for('categorias.categorias_receitas'))
        
        # Verificar se há receitas usando esta subcategoria
        receitas = conn.execute('SELECT COUNT(*) FROM receita WHERE subcategoria_id = ? AND usuario_id = ?', (id, user_id)).fetchone()[0]
        if receitas > 0:
            flash(f'Não é possível excluir esta subcategoria pois ela possui {receitas} receita(s) associada(s).', 'error')
            return redirect(url_for('categorias.categorias_receitas'))
        
        conn.execute('DELETE FROM subcategoria_receita WHERE id = ? AND usuario_id = ?', (id, user_id))
        conn.commit()
        flash('Subcategoria excluída com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao excluir subcategoria: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('categorias.categorias_receitas'))

@categorias_bp.route('/receitas/subcategoria/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_subcategoria_receita(id):
    user_id = get_current_user_id()
    conn = get_db_connection()
    subcategoria = conn.execute('''
        SELECT sr.*, cr.nome as categoria_nome 
        FROM subcategoria_receita sr 
        JOIN categoria_receita cr ON sr.categoria_id = cr.id 
        WHERE sr.id = ? AND sr.usuario_id = ? AND cr.usuario_id = ?
    ''', (id, user_id, user_id)).fetchone()
    
    if not subcategoria:
        flash('Subcategoria não encontrada.', 'error')
        return redirect(url_for('categorias.categorias_receitas'))
    
    if request.method == 'POST':
        nome = request.form['nome']
        descricao = request.form.get('descricao', '')
        
        if not nome:
            flash('O nome da subcategoria é obrigatório.', 'error')
            return redirect(url_for('categorias.editar_subcategoria_receita', id=id))
        
        try:
            conn.execute('UPDATE subcategoria_receita SET nome = ?, descricao = ? WHERE id = ? AND usuario_id = ?', (nome, descricao, id, user_id))
            conn.commit()
            flash('Subcategoria atualizada com sucesso!', 'success')
            return redirect(url_for('categorias.categorias_receitas'))
        except Exception as e:
            flash(f'Erro ao atualizar subcategoria: {str(e)}', 'error')
        finally:
            conn.close()
    
    conn.close()
    return render_template('categorias/form_subcategoria_receita.html', 
                         categoria={'nome': subcategoria['categoria_nome']}, 
                         subcategoria=subcategoria)
@categorias_bp.route('/receitas/subcategoria/nova/<int:categoria_id>', methods=['GET', 'POST'])
@login_required
def nova_subcategoria_receita(categoria_id):
    user_id = get_current_user_id()
    conn = get_db_connection()
    categoria = conn.execute('SELECT * FROM categoria_receita WHERE id = ? AND usuario_id = ?', (categoria_id, user_id)).fetchone()
    
    if not categoria:
        flash('Categoria não encontrada.', 'error')
        return redirect(url_for('categorias.categorias_receitas'))
    
    if request.method == 'POST':
        nome = request.form['nome']
        descricao = request.form.get('descricao', '')
        
        if not nome:
            flash('O nome da subcategoria é obrigatório.', 'error')
            return redirect(url_for('categorias.nova_subcategoria_receita', categoria_id=categoria_id))
        
        try:
            conn.execute('INSERT INTO subcategoria_receita (nome, categoria_id, descricao, usuario_id) VALUES (?, ?, ?, ?)', 
                        (nome, categoria_id, descricao, user_id))
            conn.commit()
            flash('Subcategoria criada com sucesso!', 'success')
            return redirect(url_for('categorias.categorias_receitas'))
        except Exception as e:
            flash(f'Erro ao criar subcategoria: {str(e)}', 'error')
        finally:
            conn.close()
    
    conn.close()
    return render_template('categorias/form_subcategoria_receita.html', categoria=categoria, subcategoria=None)

# Rotas para Categorias de Despesas
@categorias_bp.route('/despesas')
@login_required
def categorias_despesas():
    user_id = get_current_user_id()
    categorias = get_categorias_despesas(usuario_id=user_id)
    subcategorias = get_subcategorias_despesas(usuario_id=user_id)
    return render_template('categorias/despesas.html', categorias=categorias, subcategorias=subcategorias)

@categorias_bp.route('/despesas/nova', methods=['GET', 'POST'])
@login_required
def nova_categoria_despesa():
    if request.method == 'POST':
        nome = request.form['nome']
        descricao = request.form.get('descricao', '')
        user_id = get_current_user_id()
        
        if not nome:
            flash('O nome da categoria é obrigatório.', 'error')
            return redirect(url_for('categorias.nova_categoria_despesa'))
        
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO categoria_despesa (nome, descricao, usuario_id) VALUES (?, ?, ?)', (nome, descricao, user_id))
            conn.commit()
            flash('Categoria de despesa criada com sucesso!', 'success')
            return redirect(url_for('categorias.categorias_despesas'))
        except Exception as e:
            if 'UNIQUE constraint failed' in str(e):
                flash('Você já possui uma categoria com este nome.', 'error')
            else:
                flash(f'Erro ao criar categoria: {str(e)}', 'error')
        finally:
            conn.close()
    
    return render_template('categorias/form_categoria_despesa.html', categoria=None)

@categorias_bp.route('/despesas/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_categoria_despesa(id):
    user_id = get_current_user_id()
    conn = get_db_connection()
    categoria = conn.execute('SELECT * FROM categoria_despesa WHERE id = ? AND usuario_id = ?', (id, user_id)).fetchone()
    
    if not categoria:
        flash('Categoria não encontrada.', 'error')
        return redirect(url_for('categorias.categorias_despesas'))
    
    if request.method == 'POST':
        nome = request.form['nome']
        descricao = request.form.get('descricao', '')
        
        if not nome:
            flash('O nome da categoria é obrigatório.', 'error')
            return redirect(url_for('categorias.editar_categoria_despesa', id=id))
        
        try:
            conn.execute('UPDATE categoria_despesa SET nome = ?, descricao = ? WHERE id = ? AND usuario_id = ?', (nome, descricao, id, user_id))
            conn.commit()
            flash('Categoria atualizada com sucesso!', 'success')
            return redirect(url_for('categorias.categorias_despesas'))
        except Exception as e:
            flash(f'Erro ao atualizar categoria: {str(e)}', 'error')
        finally:
            conn.close()
    
    conn.close()
    return render_template('categorias/form_categoria_despesa.html', categoria=categoria)

@categorias_bp.route('/despesas/<int:id>/excluir', methods=['POST'])
@login_required
def excluir_categoria_despesa(id):
    user_id = get_current_user_id()
    conn = get_db_connection()
    try:
        # Verificar se a categoria pertence ao usuário
        categoria = conn.execute('SELECT * FROM categoria_despesa WHERE id = ? AND usuario_id = ?', (id, user_id)).fetchone()
        if not categoria:
            flash('Categoria não encontrada.', 'error')
            return redirect(url_for('categorias.categorias_despesas'))
        
        # Verificar se há despesas usando esta categoria
        despesas = conn.execute('SELECT COUNT(*) FROM despesa WHERE categoria_id = ? AND usuario_id = ?', (id, user_id)).fetchone()[0]
        if despesas > 0:
            flash(f'Não é possível excluir esta categoria pois ela possui {despesas} despesa(s) associada(s).', 'error')
            return redirect(url_for('categorias.categorias_despesas'))
        
        # Excluir subcategorias primeiro
        conn.execute('DELETE FROM subcategoria_despesa WHERE categoria_id = ? AND usuario_id = ?', (id, user_id))
        # Excluir categoria
        conn.execute('DELETE FROM categoria_despesa WHERE id = ? AND usuario_id = ?', (id, user_id))
        conn.commit()
        flash('Categoria e suas subcategorias excluídas com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao excluir categoria: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('categorias.categorias_despesas'))

@categorias_bp.route('/despesas/subcategoria/<int:id>/excluir', methods=['POST'])
@login_required
def excluir_subcategoria_despesa(id):
    user_id = get_current_user_id()
    conn = get_db_connection()
    try:
        # Verificar se a subcategoria pertence ao usuário
        subcategoria = conn.execute('SELECT * FROM subcategoria_despesa WHERE id = ? AND usuario_id = ?', (id, user_id)).fetchone()
        if not subcategoria:
            flash('Subcategoria não encontrada.', 'error')
            return redirect(url_for('categorias.categorias_despesas'))
        
        # Verificar se há despesas usando esta subcategoria
        despesas = conn.execute('SELECT COUNT(*) FROM despesa WHERE subcategoria_id = ? AND usuario_id = ?', (id, user_id)).fetchone()[0]
        if despesas > 0:
            flash(f'Não é possível excluir esta subcategoria pois ela possui {despesas} despesa(s) associada(s).', 'error')
            return redirect(url_for('categorias.categorias_despesas'))
        
        conn.execute('DELETE FROM subcategoria_despesa WHERE id = ? AND usuario_id = ?', (id, user_id))
        conn.commit()
        flash('Subcategoria excluída com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao excluir subcategoria: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('categorias.categorias_despesas'))

@categorias_bp.route('/despesas/subcategoria/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_subcategoria_despesa(id):
    user_id = get_current_user_id()
    conn = get_db_connection()
    subcategoria = conn.execute('''
        SELECT sd.*, cd.nome as categoria_nome 
        FROM subcategoria_despesa sd 
        JOIN categoria_despesa cd ON sd.categoria_id = cd.id 
        WHERE sd.id = ? AND sd.usuario_id = ? AND cd.usuario_id = ?
    ''', (id, user_id, user_id)).fetchone()
    
    if not subcategoria:
        flash('Subcategoria não encontrada.', 'error')
        return redirect(url_for('categorias.categorias_despesas'))
    
    if request.method == 'POST':
        nome = request.form['nome']
        descricao = request.form.get('descricao', '')
        
        if not nome:
            flash('O nome da subcategoria é obrigatório.', 'error')
            return redirect(url_for('categorias.editar_subcategoria_despesa', id=id))
        
        try:
            conn.execute('UPDATE subcategoria_despesa SET nome = ?, descricao = ? WHERE id = ? AND usuario_id = ?', (nome, descricao, id, user_id))
            conn.commit()
            flash('Subcategoria atualizada com sucesso!', 'success')
            return redirect(url_for('categorias.categorias_despesas'))
        except Exception as e:
            flash(f'Erro ao atualizar subcategoria: {str(e)}', 'error')
        finally:
            conn.close()
    
    conn.close()
    return render_template('categorias/form_subcategoria_despesa.html', 
                         categoria={'nome': subcategoria['categoria_nome']}, 
                         subcategoria=subcategoria)

@categorias_bp.route('/despesas/subcategoria/nova/<int:categoria_id>', methods=['GET', 'POST'])
@login_required
def nova_subcategoria_despesa(categoria_id):
    user_id = get_current_user_id()
    conn = get_db_connection()
    categoria = conn.execute('SELECT * FROM categoria_despesa WHERE id = ? AND usuario_id = ?', (categoria_id, user_id)).fetchone()
    
    if not categoria:
        flash('Categoria não encontrada.', 'error')
        return redirect(url_for('categorias.categorias_despesas'))
    
    if request.method == 'POST':
        nome = request.form['nome']
        descricao = request.form.get('descricao', '')
        
        if not nome:
            flash('O nome da subcategoria é obrigatório.', 'error')
            return redirect(url_for('categorias.nova_subcategoria_despesa', categoria_id=categoria_id))
        
        try:
            conn.execute('INSERT INTO subcategoria_despesa (nome, categoria_id, descricao, usuario_id) VALUES (?, ?, ?, ?)', 
                        (nome, categoria_id, descricao, user_id))
            conn.commit()
            flash('Subcategoria criada com sucesso!', 'success')
            return redirect(url_for('categorias.categorias_despesas'))
        except Exception as e:
            flash(f'Erro ao criar subcategoria: {str(e)}', 'error')
        finally:
            conn.close()
    
    conn.close()
    return render_template('categorias/form_subcategoria_despesa.html', categoria=categoria, subcategoria=None)
