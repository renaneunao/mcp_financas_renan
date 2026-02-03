# Chaves SSH para VPS

Este diretório contém as chaves SSH para acessar o VPS sem senha.

## Arquivos

- `vps_key` - Chave privada SSH
- `vps_key.pub` - Chave pública SSH

## Como usar

### Conectar no VPS:
```bash
ssh -i .ssh/vps_key root@194.163.142.108
```

### Copiar arquivos para o VPS:
```bash
scp -i .ssh/vps_key arquivo.txt root@194.163.142.108:~/projetos/
```

### Copiar arquivos do VPS:
```bash
scp -i .ssh/vps_key root@194.163.142.108:~/projetos/arquivo.txt ./
```

## Segurança

⚠️ **IMPORTANTE**: 
- Nunca commite a chave privada (`vps_key`) no Git
- Mantenha as chaves em local seguro
- Use permissões adequadas: `chmod 600 .ssh/vps_key`

## Configuração do .gitignore

Certifique-se de que o `.gitignore` inclui:
```
.ssh/vps_key
.ssh/vps_key.pub
```

## VPS Details

- **IP**: 194.163.142.108
- **Usuário**: root
- **Porta**: 22 (padrão SSH)



