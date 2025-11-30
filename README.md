
# Simulação de Protocolo RDT (Reliable Data Transfer) sobre TCP

Este projeto implementa uma simulação robusta de protocolos de transferência confiável de dados (RDT) utilizando Sockets em Python. O sistema emula o comportamento da camada de transporte, demonstrando visualmente o funcionamento de janelas deslizantes, criptografia e tratamento de erros.

---

## Funcionalidades Implementadas

O projeto suporta dois modos de operação de janelas deslizantes (**Sliding Windows**):

1. **Go-Back-N (GBN):** Utiliza ACKs cumulativos. Se ocorrer erro ou timeout, retransmite toda a janela a partir do pacote perdido.  
2. **Selective Repeat (SR):** Utiliza ACKs individuais. Retransmite apenas os pacotes específicos que foram perdidos ou corrompidos.

### Destaques Técnicos

- **Handshake de 3 Vias:** Estabelecimento de conexão (SYN, SYN-ACK, ACK) antes da transferência.  
- **Segurança:** Criptografia simétrica de ponta a ponta utilizando a biblioteca `cryptography` (Fernet).  
- **Checksum:** Verificação de integridade para detectar dados corrompidos.  
- **Simulação de Erros Interativa:** Permite injetar falhas propositais para testar a robustez:  
  - Perda de pacotes (simulada)  
  - Corrupção de bits  
  - Pacotes duplicados  
  - Timeout (atraso na resposta)  

---

## Instalação

Para rodar este projeto, você precisa do **Python 3.x** instalado.  
Além disso, é necessário instalar a biblioteca de criptografia:

pip install cryptography

---

##  Estrutura dos Arquivos

Certifique-se de que os arquivos do projeto estejam nomeados exatamente desta forma na mesma pasta:

- `client.py` ➝ O código do cliente (interface de envio).  
- `server.py` ➝ O código do servidor (recebimento e ACKs).  
- `security.py` ➝ O módulo de segurança (classe `SecurityManager`).  

---

##  Como Executar

O sistema funciona em arquitetura Cliente-Servidor. Você precisará de dois terminais abertos.

### 1. Iniciar o Servidor

No primeiro terminal, execute o servidor. Ele ficará escutando na porta `1500`.

python server.py

### 2. Iniciar o Cliente

No segundo terminal, execute o cliente.

python client.py

---

##  Guia de Uso 

Após iniciar o `client.py`, siga as instruções no terminal:

1. **Escolha o Protocolo:**  
   - Digite `1` para **Go-Back-N**  
   - Digite `2` para **Repetição Seletiva**  

2. **Configuração de Erros (Opcional):**  
   O sistema perguntará se deseja simular erros.  
   Se "Sim", você pode escolher qual tipo de erro (ex: Timeout, Perda) deseja forçar para ver o protocolo reagindo.  

3. **Tamanho da Janela (Apenas GBN):**  
   Defina quantos pacotes podem ser enviados sem confirmação (Ex: 4).  

4. **Envio de Mensagem:**  
   - Digite a frase que deseja enviar.  
   - O programa irá fragmentar a frase em pacotes pequenos (4 caracteres), criptografar o conteúdo e enviar seguindo a lógica da janela escolhida.  
   - Acompanhe no terminal o status de cada pacote (`SEQ`), os `ACKs` recebidos e eventuais retransmissões.  

---

##  Detalhes de Configuração

- **Porta:** 1500 (Localhost)  
- **Timeout de Retransmissão:** 3.0 segundos  
- **Fragmentação:** As mensagens são divididas em blocos de 4 caracteres para facilitar a visualização didática do fluxo de muitos pacotes

## Integrantes do Grupo

- Arthur Apolinário
- Antônio Laprovitera
- Felipe Andrade
- Gabriel Tabosa
- Guilherme Vinícius
- Letícia Soares
- Pedro Gusmão