from flask import Flask
from app.database import init_db
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
    app.config['SECRET_KEY'] = 'financas_renan_secret_key'
    app.config['DATABASE'] = 'financas.db'
    
    # Adicionar filtro personalizado para datas
    app.jinja_env.filters['date_br'] = format_date_br
    
    # Inicializar banco de dados
    init_db()
    
    # Registrar blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(receitas_bp)
    app.register_blueprint(despesas_bp)
    app.register_blueprint(categorias_bp)
    
    return app
