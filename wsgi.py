from app import create_app

# Criar instância da aplicação para WSGI
app = create_app()

if __name__ == "__main__":
    # Para desenvolvimento local
    app.run(host='0.0.0.0', port=8000, debug=False)