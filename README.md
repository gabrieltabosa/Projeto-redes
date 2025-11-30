Projeto de Comunicação Confiável com Criptografia
Sistema cliente-servidor que implementa dois protocolos de rede confiáveis (Go-Back-N e Repetição Seletiva) com criptografia integrada. Permite simular diversos tipos de erro em redes e testar a robustez dos protocolos.

Integrantes
Antônio Augusto

Pedro Gusmão

Felipe Andrade

Gabriel Tabosa

Guilherme Vinicius

Leticia Soares

Como Executar
1. Criar e ativar ambiente virtual (recomendado)
bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate

2. Instalar dependência no ambiente virtual
bash
pip install cryptography

3. Executar o servidor (Terminal 1)
bash
python server.py

4. Executar o cliente (Terminal 2)
bash
python client.py

5. Seguir os passos no cliente:
Escolher modo (1-GBN ou 2-SR)

Opcional: simular erros (timeout, perda, corrupção, duplicação)

Definir tamanho da janela (1-5 pacotes)

Digitar mensagens para enviar

Digitar "sair" para encerrar

Funcionalidades: Handshake de 3 vias, checksum, criptografia AES, retransmissão, controle de congestionamento.
