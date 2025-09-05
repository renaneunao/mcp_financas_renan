FROM python:3.9-slim

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Criar usuário não-root para segurança
RUN useradd --create-home --shell /bin/bash app

WORKDIR /app

# Copiar e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalar gunicorn
RUN pip install --no-cache-dir gunicorn

# Copiar código da aplicação
COPY . .

# Criar diretório para dados e dar permissões
RUN mkdir -p /data && chown -R app:app /app /data

# Mudar para usuário não-root
USER app

# Expor a porta que o gunicorn vai usar
EXPOSE 8000

# Comando para rodar a aplicação com gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--threads", "2", "--timeout", "120", "wsgi:app"]