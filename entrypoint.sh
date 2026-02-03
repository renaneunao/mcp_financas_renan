#!/bin/sh

# Espera o banco de dados estar disponível (se aplicável, para garantir que o volume esteja montado)
# sleep 5

# Define o proprietário e as permissões corretas para o arquivo do banco de dados
chown app:app /data/financas.db
chmod 666 /data/financas.db

# Executa o comando original da aplicação (Gunicorn)
exec gunicorn --bind 0.0.0.0:8000 --workers 4 --threads 2 wsgi:app


