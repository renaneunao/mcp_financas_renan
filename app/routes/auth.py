from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from app.database import get_db_connection, gerar_parcelas_receita, gerar_parcelas_despesa
import hashlib
import os
from datetime import date
from werkzeug.utils import secure_filename
from PIL import Image

auth_bp = Blueprint('auth', __name__)

def hash_password(password):
    """Gera hash da senha usando SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def check_password(password, hashed):
    """Verifica se a senha está correta"""
    return hash_password(password) == hashed

def criar_categorias_padrao(usuario_id):
    """Cria categorias e subcategorias padrão para um novo usuário"""
    conn = get_db_connection()
    
    # Categorias e subcategorias de receitas
    categorias_receitas = {
        'Salário': ['Salário Principal', 'Décimo Terceiro', 'Férias', 'PLR'],
        'Freelance': ['Projetos', 'Consultoria', 'Trabalhos Extras'],
        'Investimentos': ['Dividendos', 'Rendimentos', 'Ganho Capital'],
        'Outros': ['Vendas', 'Reembolsos', 'Presentes']
    }
    
    # Categorias e subcategorias de despesas
    categorias_despesas = {
        'Moradia': ['Aluguel/Financiamento', 'Condomínio', 'IPTU', 'Seguro Residencial'],
        'Alimentação': ['Supermercado', 'Restaurantes', 'Delivery', 'Lanchonetes'],
        'Transporte': ['Combustível', 'Uber/Táxi', 'Transporte Público', 'Manutenção Veículo'],
        'Saúde': ['Plano de Saúde', 'Medicamentos', 'Consultas', 'Exames'],
        'Educação': ['Cursos', 'Livros', 'Material Escolar', 'Universidade'],
        'Lazer': ['Cinema', 'Viagens', 'Streaming', 'Hobbies'],
        'Vestuário': ['Roupas', 'Calçados', 'Acessórios'],
        'Utilidades': ['Energia Elétrica', 'Água', 'Internet', 'Telefone', 'Gás'],
        'Outros': ['Impostos', 'Taxas', 'Diversos']
    }
    
    try:
        # Inserir categorias e subcategorias de receitas
        for categoria_nome, subcategorias in categorias_receitas.items():
            categoria_id = conn.execute(
                '''INSERT INTO categoria_receita (nome, usuario_id) VALUES (?, ?)''',
                (categoria_nome, usuario_id)
            ).lastrowid
            
            for subcategoria_nome in subcategorias:
                conn.execute(
                    '''INSERT INTO subcategoria_receita (nome, categoria_id, usuario_id) VALUES (?, ?, ?)''',
                    (subcategoria_nome, categoria_id, usuario_id)
                )
        
        # Inserir categorias e subcategorias de despesas
        for categoria_nome, subcategorias in categorias_despesas.items():
            categoria_id = conn.execute(
                '''INSERT INTO categoria_despesa (nome, usuario_id) VALUES (?, ?)''',
                (categoria_nome, usuario_id)
            ).lastrowid
            
            for subcategoria_nome in subcategorias:
                conn.execute(
                    '''INSERT INTO subcategoria_despesa (nome, categoria_id, usuario_id) VALUES (?, ?, ?)''',
                    (subcategoria_nome, categoria_id, usuario_id)
                )
        
        conn.commit()
        print(f"✅ Categorias padrão criadas para usuário {usuario_id}")
        
    except Exception as e:
        print(f"❌ Erro ao criar categorias padrão: {e}")
        conn.rollback()
    finally:
        conn.close()

def criar_lancamentos_exemplo(usuario_id):
    """Cria lançamentos de exemplo para um novo usuário"""
    conn = get_db_connection()
    
    try:
        # Obter primeira categoria e subcategoria de receita
        categoria_receita = conn.execute(
            'SELECT id FROM categoria_receita WHERE usuario_id = ? ORDER BY id LIMIT 1',
            (usuario_id,)
        ).fetchone()
        
        subcategoria_receita = conn.execute(
            'SELECT id FROM subcategoria_receita WHERE usuario_id = ? ORDER BY id LIMIT 1',
            (usuario_id,)
        ).fetchone()
        
        # Obter primeira categoria e subcategoria de despesa
        categoria_despesa = conn.execute(
            'SELECT id FROM categoria_despesa WHERE usuario_id = ? ORDER BY id LIMIT 1',
            (usuario_id,)
        ).fetchone()
        
        subcategoria_despesa = conn.execute(
            'SELECT id FROM subcategoria_despesa WHERE usuario_id = ? ORDER BY id LIMIT 1',
            (usuario_id,)
        ).fetchone()
        
        data_hoje = date.today().strftime('%Y-%m-%d')
        
        # Criar receita de exemplo (Salário)
        if categoria_receita:
            gerar_parcelas_receita(
                categoria_id=categoria_receita['id'],
                subcategoria_id=subcategoria_receita['id'] if subcategoria_receita else None,
                data_inicio=data_hoje,
                data_fim=None,
                tipo_recorrencia='unica',
                valor_parcela=5000.00,  # R$ 5.000,00
                dia_comum=None,
                user_id=usuario_id
            )
            print(f"✅ Receita de exemplo criada para usuário {usuario_id}: R$ 5.000,00")
        
        # Criar despesa de exemplo (Moradia)
        if categoria_despesa:
            gerar_parcelas_despesa(
                categoria_id=categoria_despesa['id'],
                subcategoria_id=subcategoria_despesa['id'] if subcategoria_despesa else None,
                data_inicio=data_hoje,
                data_fim=None,
                tipo_recorrencia='unica',
                valor_parcela=1200.00,  # R$ 1.200,00
                dia_comum=None,
                user_id=usuario_id
            )
            print(f"✅ Despesa de exemplo criada para usuário {usuario_id}: R$ 1.200,00")
    
    except Exception as e:
        print(f"❌ Erro ao criar lançamentos de exemplo para usuário {usuario_id}: {e}")
    
    finally:
        conn.close()

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute(
            'SELECT * FROM usuario WHERE username = ? AND ativo = 1',
            (username,)
        ).fetchone()
        conn.close()
        
        if user and check_password(password, user['password_hash']):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['nome_completo'] = user['nome_completo']
            flash(f'Bem-vindo, {user["nome_completo"] or user["username"]}!', 'success')
            
            # Redirecionar para a página solicitada ou dashboard
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard.index'))
        else:
            flash('Usuário ou senha incorretos', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    """Logout do usuário"""
    nome = session.get('nome_completo') or session.get('username')
    session.clear()
    flash(f'Até logo, {nome}!', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Página de registro de novos usuários"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        nome_completo = request.form['nome_completo']
        email = request.form.get('email', '')
        
        # Validações
        if len(username) < 3:
            flash('Nome de usuário deve ter pelo menos 3 caracteres', 'error')
            return render_template('auth/register.html')
        
        if len(password) < 6:
            flash('Senha deve ter pelo menos 6 caracteres', 'error')
            return render_template('auth/register.html')
            
        if password != confirm_password:
            flash('Senhas não coincidem', 'error')
            return render_template('auth/register.html')
        
        conn = get_db_connection()
        
        # Verificar se usuário já existe
        existing_user = conn.execute(
            'SELECT id FROM usuario WHERE username = ?',
            (username,)
        ).fetchone()
        
        if existing_user:
            flash('Nome de usuário já existe', 'error')
            conn.close()
            return render_template('auth/register.html')
        
        # Criar novo usuário
        password_hash = hash_password(password)
        cursor = conn.execute(
            '''INSERT INTO usuario (username, password_hash, nome_completo, email)
               VALUES (?, ?, ?, ?)''',
            (username, password_hash, nome_completo, email)
        )
        usuario_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Criar categorias padrão para o novo usuário
        criar_categorias_padrao(usuario_id)
        
        # Criar lançamentos de exemplo para o novo usuário
        criar_lancamentos_exemplo(usuario_id)
        
        flash('Usuário criado com sucesso! Categorias padrão e lançamentos de exemplo foram adicionados automaticamente. Faça login para continuar.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')

def login_required(f):
    """Decorator para proteger rotas que precisam de login"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Você precisa fazer login para acessar esta página', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user_id():
    """Retorna o ID do usuário logado"""
    return session.get('user_id')

@auth_bp.route('/profile')
@login_required
def profile():
    """Página do perfil do usuário"""
    conn = get_db_connection()
    user = conn.execute(
        'SELECT id, username, nome_completo, email FROM usuario WHERE id = ?',
        (get_current_user_id(),)
    ).fetchone()
    conn.close()
    
    if not user:
        flash('Usuário não encontrado', 'error')
        return redirect(url_for('auth.logout'))
    
    return render_template('auth/profile.html', user=user)

@auth_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    """Atualiza o perfil do usuário"""
    nome = request.form['nome']
    senha_atual = request.form.get('senha_atual', '')
    nova_senha = request.form.get('nova_senha', '')
    confirmar_senha = request.form.get('confirmar_senha', '')
    
    if not nome.strip():
        flash('Nome é obrigatório', 'error')
        return redirect(url_for('auth.profile'))
    
    conn = get_db_connection()
    user = conn.execute(
        'SELECT id, username, nome_completo, email, password_hash FROM usuario WHERE id = ?',
        (get_current_user_id(),)
    ).fetchone()
    
    if not user:
        flash('Usuário não encontrado', 'error')
        conn.close()
        return redirect(url_for('auth.logout'))
    
    # Se o usuário quer alterar a senha
    if nova_senha:
        if not senha_atual:
            flash('Senha atual é obrigatória para alterar a senha', 'error')
            conn.close()
            return redirect(url_for('auth.profile'))
        
        if not check_password(senha_atual, user['password_hash']):
            flash('Senha atual incorreta', 'error')
            conn.close()
            return redirect(url_for('auth.profile'))
        
        if nova_senha != confirmar_senha:
            flash('Confirmação de senha não confere', 'error')
            conn.close()
            return redirect(url_for('auth.profile'))
        
        if len(nova_senha) < 6:
            flash('Nova senha deve ter pelo menos 6 caracteres', 'error')
            conn.close()
            return redirect(url_for('auth.profile'))
        
        # Atualiza nome e senha
        hashed_password = hash_password(nova_senha)
        conn.execute(
            'UPDATE usuario SET nome_completo = ?, password_hash = ? WHERE id = ?',
            (nome.strip(), hashed_password, get_current_user_id())
        )
        flash('Perfil e senha atualizados com sucesso!', 'success')
    else:
        # Atualiza apenas o nome
        conn.execute(
            'UPDATE usuario SET nome_completo = ? WHERE id = ?',
            (nome.strip(), get_current_user_id())
        )
        flash('Perfil atualizado com sucesso!', 'success')
    
    conn.commit()
    conn.close()
    
    return redirect(url_for('auth.profile'))

@auth_bp.route('/upload-photo', methods=['POST'])
@login_required
def upload_photo():
    """Upload de foto de perfil"""
    try:
        if 'photo' not in request.files:
            return jsonify({'success': False, 'message': 'Nenhum arquivo enviado'})
        
        file = request.files['photo']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'Nenhum arquivo selecionado'})
        
        # Validar tipo de arquivo
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
        if not ('.' in file.filename and 
                file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
            return jsonify({'success': False, 'message': 'Tipo de arquivo não permitido'})
        
        # Obter username do usuário logado
        username = session.get('username')
        if not username:
            return jsonify({'success': False, 'message': 'Usuário não autenticado'})
        
        # Definir caminho do arquivo
        upload_folder = 'app/static/img/profile_users'
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
        
        # Nome do arquivo será sempre o username + .jpg
        filename = f"{username}.jpg"
        filepath = os.path.join(upload_folder, filename)
        
        # Processar e salvar a imagem
        try:
            # Usar PIL se disponível, senão salvar diretamente
            from PIL import Image
            
            # Abrir a imagem
            img = Image.open(file.stream)
            
            # Converter para RGB se necessário (para garantir compatibilidade com JPEG)
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # Redimensionar para 200x200 mantendo proporção
            img.thumbnail((200, 200), Image.Resampling.LANCZOS)
            
            # Criar uma nova imagem quadrada 200x200 com fundo branco
            new_img = Image.new('RGB', (200, 200), (255, 255, 255))
            
            # Calcular posição para centralizar a imagem
            x = (200 - img.width) // 2
            y = (200 - img.height) // 2
            
            # Colar a imagem redimensionada no centro
            new_img.paste(img, (x, y))
            
            # Salvar como JPEG
            new_img.save(filepath, 'JPEG', quality=85, optimize=True)
            
        except ImportError:
            # Se PIL não estiver disponível, salvar o arquivo diretamente
            file.seek(0)  # Voltar ao início do arquivo
            file.save(filepath)
        
        # URL da foto para retornar
        photo_url = url_for('static', filename=f'img/profile_users/{filename}')
        
        return jsonify({
            'success': True, 
            'message': 'Foto atualizada com sucesso!',
            'photo_url': photo_url
        })
        
    except Exception as e:
        print(f"Erro no upload de foto: {e}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'})


@auth_bp.route('/remove-photo', methods=['POST'])
@login_required
def remove_photo():
    """Remove a foto de perfil do usuário"""
    try:
        username = session['username']
        
        # Caminho da foto
        filepath = os.path.join(current_app.static_folder, 'img', 'profile_users', f'{username}.jpg')
        
        # Verificar se o arquivo existe e removê-lo
        if os.path.exists(filepath):
            os.remove(filepath)
            return jsonify({
                'success': True, 
                'message': 'Foto removida com sucesso!'
            })
        else:
            return jsonify({
                'success': True, 
                'message': 'Nenhuma foto para remover'
            })
        
    except Exception as e:
        print(f"Erro ao remover foto: {e}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'})
