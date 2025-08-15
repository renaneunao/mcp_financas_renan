from flask import Flask
from app.database import init_db
from app.routes.dashboard import dashboard_bp
from app.routes.receitas import receitas_bp
from app.routes.despesas import despesas_bp
from app.routes.categorias import categorias_bp
from app.routes.auth import auth_bp

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'financas_renan_secret_key'
    app.config['DATABASE'] = 'financas.db'
    
    # Inicializar banco de dados
    init_db()
    
    # Registrar blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(receitas_bp)
    app.register_blueprint(despesas_bp)
    app.register_blueprint(categorias_bp)
    
    return app
