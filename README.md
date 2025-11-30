📡 Simulador de Protocolos de Rede Confiável (GBN & SR)
Este projeto implementa uma simulação robusta de protocolos de transferência de dados confiável sobre uma camada de transporte, utilizando Python. O sistema simula o comportamento da camada de transporte, implementando controle de fluxo, verificação de integridade e retransmissão, além de adicionar uma camada de criptografia.

O projeto foca na demonstração prática dos algoritmos Go-Back-N (GBN) e Repetição Seletiva (Selective Repeat), permitindo a injeção deliberada de erros (perda, corrupção, duplicação) para visualizar como os protocolos reagem.

🚀 Funcionalidades Principais
Protocolos de Janela Deslizante:

✅ Go-Back-N: Retransmissão cumulativa com descarte de pacotes fora de ordem.

✅ Repetição Seletiva: Retransmissão individual apenas dos pacotes perdidos/corrompidos.

Conexão (Handshake): Implementação de um 3-Way Handshake (SYN, SYN-ACK, ACK) com negociação de parâmetros.

Segurança (Criptografia): Criptografia ponta-a-ponta utilizando Fernet (Symmetric Encryption) para proteger o payload das mensagens.

Integridade de Dados: Cálculo e validação de Checksum para detectar corrupção de pacotes.

Simulação de Erros Controlada:

Simulação de Timeout.

Duplicação de pacotes.

Perda Garantida de pacotes (sorteio aleatório).

Corrupção de Bits (alteração do payload para falhar no checksum).

Segmentação: Divisão automática de mensagens longas em pacotes menores.

📂 Estrutura do Projeto
server.py: O servidor que escuta conexões, processa o handshake, recebe pacotes, verifica checksums, desencripta mensagens e envia ACKs/NACKs.

client.py: O cliente que inicia a conexão, permite ao usuário configurar o protocolo e erros, segmenta a mensagem, encripta e envia os dados.

security.py: Módulo responsável pelo gerenciamento de chaves e funções de encriptar/desencriptar usando a biblioteca cryptography.

🛠️ Pré-requisitos
Para executar este projeto, você precisará do Python 3.x e da biblioteca externa cryptography.

Instalação das dependências
Execute o comando abaixo no terminal para instalar a biblioteca necessária:

Bash

pip install cryptography
▶️ Como Executar
O sistema funciona com uma arquitetura Cliente-Servidor. Você precisará de dois terminais abertos.

Passo 1: Iniciar o Servidor
No primeiro terminal, execute o servidor. Ele ficará aguardando conexões na porta 1500.

Bash

python server.py
Passo 2: Iniciar o Cliente
No segundo terminal, execute o cliente.

Bash

python client.py
Passo 3: Interação
O cliente solicitará configurações interativas:

Escolha do Protocolo: Digite 1 para Go-Back-N ou 2 para Repetição Seletiva.

Simulação de Erros: Escolha se deseja simular falhas na rede (detalhes abaixo).

Tamanho da Janela: Defina quantos pacotes podem ser enviados sem confirmação (apenas GBN).

Envio de Mensagem: Digite a mensagem que deseja enviar.

🧪 Modos de Simulação de Erro
Durante a configuração do cliente, você pode escolher um dos seguintes cenários para testar a robustez do protocolo:

Timeout Erro: Simula um atraso que estoura o temporizador, forçando retransmissão.

Pacote Duplicado: Envia o mesmo pacote múltiplas vezes para testar o descarte no servidor.

Perda de Pacotes (Garantida): Escolhe aleatoriamente um pacote da janela para "desaparecer", forçando o protocolo a lidar com a lacuna de sequência.

Pacote Corrompido: Altera bits do pacote propositalmente para que a validação de Checksum falhe no servidor.

🔐 Detalhes Técnicos
Estrutura do Pacote
Os pacotes trafegam na rede simulada (socket) no seguinte formato string (antes da codificação para bytes):

Plaintext

FLAG | DADOS_ENCRIPTADOS | NUM_SEQUENCIA | CHECKSUM
FLAG: Indica o tipo (ex: MSG, SYN, ACK).

DADOS: Payload criptografado via Fernet.

SEQ: Número de sequência para ordenação.

CHECKSUM: Inteiro calculado pela soma dos ordinais dos caracteres modulo 65536.

Segurança
O sistema utiliza a classe SecurityManager que implementa Fernet (AES). Uma chave simétrica hardcoded (SHARED_KEY) é compartilhada entre cliente e servidor para fins de demonstração, garantindo que, se um pacote for interceptado (sniffing), o conteúdo estará ilegível.

📝 Autor
Desenvolvido como parte de um projeto de estudo sobre Redes de Computadores, focado na camada de transporte e algoritmos de confiabilidade.
