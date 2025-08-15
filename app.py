import os
import ssl
from app import create_app

app = create_app()

if __name__ == '__main__':
    # Caminhos dos arquivos de certificado
    cert_file = './certs/cert.cert'
    key_file = './certs/private.key'

    # Verificar se os arquivos de certificado existem
    if not os.path.exists(cert_file):
        print(f"❌ Erro: Arquivo de certificado não encontrado em: {cert_file}")
        exit(1)
    if not os.path.exists(key_file):
        print(f"❌ Erro: Arquivo de chave privada não encontrado em: {key_file}")
        exit(1)

    # Configurar contexto SSL
    try:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(certfile=cert_file, keyfile=key_file)
        print("✅ Certificados SSL carregados com sucesso")
    except ssl.SSLError as e:
        print(f"❌ Erro ao carregar certificados SSL: {e}")
        exit(1)

    # Iniciar o servidor Flask com SSL
    try:
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=True,
            ssl_context=ssl_context
        )
    except Exception as e:
        print(f"❌ Erro ao iniciar o servidor: {e}")