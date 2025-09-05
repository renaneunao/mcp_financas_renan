import os
from flask import Flask
from init_db import init_db
from app.database import get_db_connection
from app.routes.dashboard import dashboard_bp
from app.routes.receitas import receitas_bp
from app.routes.despesas import despesas_bp
from app.routes.categorias import categorias_bp
from app.routes.auth import auth_bp
from datetime import datetime

def format_date_br(date_string):
    """Converte data do formato YYYY-MM-DD para DD/MM/YYYY"""
    if not date_string:
        return ''
    
    try:
        # Se já é uma string no formato ISO, converte
        if isinstance(date_string, str):
            date_obj = datetime.strptime(date_string, '%Y-%m-%d')
        elif isinstance(date_string, datetime):
            date_obj = date_string
        else:
            return str(date_string)
        
        return date_obj.strftime('%d/%m/%Y')
    except (ValueError, TypeError):
        return str(date_string)

def create_app():
    app = Flask(__name__)
    
    # Configurações da aplicação
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
    app.config['DATABASE'] = os.environ.get('DB_PATH', 'financas.db')
    
    # Configurações de segurança
    app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    
    # Filtro personalizado para datas
    app.jinja_env.filters['date_br'] = format_date_br
    
    # Inicializar banco de dados
    with app.app_context():
        init_db()
        # Testar conexão com o banco de dados
        try:
            conn = get_db_connection()
            conn.execute('SELECT 1')
            app.logger.info('Conexão com o banco de dados estabelecida com sucesso')
        except Exception as e:
            app.logger.error(f'Erro ao conectar ao banco de dados: {e}')
            raise
    
    # Registrar blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(receitas_bp)
    app.register_blueprint(despesas_bp)
    app.register_blueprint(categorias_bp)
    
    return app
