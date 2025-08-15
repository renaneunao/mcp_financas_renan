# Sistema de Controle Financeiro Pessoal

Um sistema web para controle de finanças pessoais desenvolvido com Flask e Tailwind CSS.

## Funcionalidades

- ✅ Autenticação de usuários
- ✅ Gerenciamento de receitas e despesas
- ✅ Categorias e subcategorias personalizáveis
- ✅ Dashboard interativo
- ✅ Upload e edição de foto de perfil com cropping
- ✅ Controle de parcelas
- ✅ Interface responsiva

## Tecnologias Utilizadas

### Backend
- Flask
- SQLite
- Pillow (processamento de imagens)
- Werkzeug

### Frontend
- Tailwind CSS (compilado localmente)
- JavaScript (Vanilla)
- Cropper.js (edição de imagens)
- Font Awesome (ícones)

## Instalação

### Pré-requisitos
- Python 3.7+
- Node.js 16+
- npm

### Configuração do Ambiente

1. Clone o repositório e navegue até o diretório:
```bash
cd financas_renan
```

2. Instale as dependências Python:
```bash
pip install -r requirements.txt
```

3. Instale as dependências Node.js:
```bash
npm install
```

4. Compile o CSS do Tailwind:
```bash
npm run build
```

## Execução

### Desenvolvimento
Para executar em modo de desenvolvimento com hot-reload do CSS:

```bash
# Terminal 1: Compilar CSS em modo watch
npm run dev

# Terminal 2: Executar servidor Flask
python app.py
```

### Produção
```bash
npm run start
```

## Estrutura do Projeto

```
financas_renan/
├── app/
│   ├── __init__.py
│   ├── database.py
│   ├── routes/
│   │   ├── auth.py
│   │   ├── dashboard.py
│   │   ├── receitas.py
│   │   ├── despesas.py
│   │   └── categorias.py
│   ├── static/
│   │   ├── css/
│   │   │   ├── input.css
│   │   │   └── output.css
│   │   └── img/
│   └── templates/
├── certs/
├── app.py
├── requirements.txt
├── package.json
├── tailwind.config.js
└── README.md
```

## Scripts Disponíveis

- `npm run dev` - Compila CSS em modo watch para desenvolvimento
- `npm run build` - Compila CSS minificado para produção
- `npm run start` - Builda CSS e inicia servidor Flask

## Certificados SSL

O projeto usa certificados SSL locais. Certifique-se de que os arquivos estejam em:
- `certs/cert.cert`
- `certs/private.key`

## Funcionalidades Principais

### Dashboard
- Visualização de receitas e despesas do mês atual
- Itens clicáveis para edição rápida
- Indicadores visuais de status

### Gestão Financeira
- Cadastro de receitas e despesas
- Suporte a parcelas
- Categorização customizável
- Edição e exclusão de lançamentos

### Perfil do Usuário
- Upload de foto de perfil
- Cropping de imagem
- Remoção de foto
- Edição de dados pessoais
- Alteração de senha

### Categorias
- Criação automática de categorias padrão
- Gestão de subcategorias
- Associação a lançamentos

## Contribuição

Este é um projeto pessoal, mas contribuições são bem-vindas através de pull requests.
