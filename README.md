# Projeto Redes – Handshake TCP Simulado

## 📌 Descrição
Este projeto por enquanto implementa um **handshake de 3 vias** (SYN → SYN-ACK → ACK) entre **Cliente** e **Servidor**, simulando o processo de estabelecimento de conexão no protocolo TCP.

- O **Servidor** fica escutando em `localhost:1500` e aguarda conexões de clientes.
- O **Cliente** se conecta ao servidor e inicia o processo de handshake.
- Durante o processo, o cliente pode escolher o **modo de operação** (GoBackN ou Repetição Seletiva) e um tamanho máximo de pacote (`1024`).

---

## ⚙️ Funcionalidades
### Cliente (`client.py`)
- Conecta ao servidor em `localhost:1500`.
- Solicita ao usuário a escolha do **modo de operação**:
  - `1` → GoBackN  
  - `2` → Repetição Seletiva  
- Envia mensagem `SYN|modo|tam_max`.
- Aguarda resposta `SYN-ACK|modo|tam_max`.
- Finaliza o handshake enviando `ACK`.

### Servidor (`server.py`)
- Cria um socket TCP escutando na porta `1500`.
- Aceita conexão de um cliente.
- Processa o `SYN` recebido, valida os parâmetros.
- Responde com `SYN-ACK|modo|tam_max`.
- Aguarda o `ACK` final do cliente.
- Exibe mensagens de log confirmando o sucesso ou falha do processo.

---

## 🚀 Como Executar

1. Abra dois terminais na pasta raiz do projeto.

### No primeiro terminal, inicie o servidor:
```bash
python3 server.py
