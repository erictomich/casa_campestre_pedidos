# Casa Campestre · Pré-pedido de pizzas

Formulário de pré-pedido para a celebração de união de **Soloína & Eric**.
Cada pedido é salvo **ao mesmo tempo** no SQLite e num backup JSON.

## Páginas

| Página | URL | O que é |
|---|---|---|
| Formulário | `/` (`index.html`) | Convite + cardápio + montagem do pedido |
| Agradecimento | `/obrigado.html` | Resumo do pedido, mostrado após o envio |
| Listagem | `/pedidos.html` | Todos os pedidos — **pede um token** |

## Como rodar

1. Instalar a dependência (só na primeira vez):

   ```bash
   pip install -r requirements.txt
   ```

2. Iniciar o servidor:

   ```bash
   python server.py
   ```

3. Abrir no navegador: <http://localhost:8000>

## Onde os pedidos ficam salvos

- **`pedidos.db`** — banco SQLite (tabela `pedidos`). Fonte principal.
- **`pedidos_backup.json`** — cópia de segurança legível, atualizada a cada pedido.

Os dois arquivos são criados automaticamente na primeira execução.

## Ver os pedidos (área restrita)

Acesse `http://localhost:8000/pedidos.html` e informe o token, ou vá direto por:

```
http://localhost:8000/pedidos.html?token=casa-campestre-2026
```

A página mostra estatísticas, um **resumo consolidado para a cozinha**
(quantos de cada sabor/tamanho no total) e a lista de todos os pedidos.

## Configuração (opcional)

Variáveis de ambiente:

| Variável | Padrão | Descrição |
|---|---|---|
| `ADMIN_TOKEN` | `casa-campestre-2026` | Token da página de listagem |
| `PORT` | `8000` | Porta do servidor |

Exemplo (PowerShell):

```powershell
$env:ADMIN_TOKEN = "meu-token-secreto"; python server.py
```

> **Nota de segurança:** o token é uma proteção simples (fica visível na URL).
> Serve bem para uso interno/evento. Não é uma autenticação forte —
> não use para dados sensíveis nem exponha na internet pública sem HTTPS.
