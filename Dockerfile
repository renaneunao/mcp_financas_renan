FROM python:3.9-slim

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instalar Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs

# Criar usuário não-root para segurança
RUN useradd --create-home --shell /bin/bash app

WORKDIR /app

# Copiar package.json e package-lock.json primeiro (para cache de dependências)
COPY package*.json ./

# Instalar dependências Node.js
RUN npm install

# Copiar e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalar gunicorn
RUN pip install --no-cache-dir gunicorn

# Copiar código da aplicação
COPY . .

# Build do Tailwind CSS
RUN npm run build

# Criar diretório para dados e dar permissões
RUN mkdir -p /data && chown -R app:app /app /data

# Mudar para usuário não-root
USER app

# Expor a porta que o gunicorn vai usar
EXPOSE 8000

# Comando para rodar a aplicação com gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--threads", "2", "--timeout", "120", "wsgi:app"]