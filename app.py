from app import create_app

app = create_app()

if __name__ == '__main__':
    # Iniciar o servidor Flask sem SSL
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )