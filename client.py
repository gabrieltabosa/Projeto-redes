import random
import socket

RETRANSMISSION_TIMEOUT = 3.0

def print_titulo(texto):
    print("\n" + "=" * 80)
    print(f"{texto.center(80)}")
    print("=" * 80 + "\n")

def handshake(sock):
    print_titulo("INICIANDO HANDSHAKE COM O SERVIDOR")

    # Escolhendo Modo de Operação
    while True:
        print(">> [CLIENTE] Escolha o Modo de Operacao para SYN:\n"
              ">> [CLIENTE] (1) GoBackN\n"
              ">> [CLIENTE] (2) Repetição Seletiva")
        escolha = input(">> [CLIENTE] Digite sua escolha: ")
        if escolha == "1":
            modo = "GoBackN"
            break
        elif escolha == "2":
            modo = "RepetiçãoSeletiva"
            break
        else:
            print("Opção inexistente! Tente novamente\n")

    # 1. Enviando SYN ao servidor
    tam_max = "1024"
    print(f"\n>> [CLIENTE] Tamanho pré-definido de mensagem: {tam_max}")
    
    mensagem = f"SYN|{modo}|{tam_max}"
    print(f"\n>> [CLIENTE] Enviando SYN para o servidor: {mensagem}")
    sock.send(mensagem.encode('utf-8'))

    # 2. Recebendo o SYN-ACK do Servidor
    print("\n>> [CLIENTE] Aguardando resposta SYN-ACK do servidor...")
    resposta = sock.recv(1024).decode('utf-8')
    print(f">> [CLIENTE] Resposta recebida: {resposta}")

    # Conferindo resposta
    partes = resposta.split("|")
    if resposta.startswith("SYN-ACK") and partes[1] == modo and partes[2] == tam_max:
        # 3. Enviando ACK ao servidor
        print("\n>> [CLIENTE] Enviando ACK para o servidor...")
        sock.send("ACK".encode('utf-8'))
        print_titulo("HANDSHAKE COM O SERVIDOR ESTABELECIDO")
    else:
        print_titulo("ERRO NO HANDSHAKE")
        raise Exception("Falha no Handshake")

def comunicacao_server(sock, message ,seq):
    flag = 'MSG'
    
    #define uma chance em 4 para perder a mensagem e flag ser PERDA, implemente de outra forma     
    if random.randint(1, 4) == 1:
        flag = 'PERDA'
        print(f"\n>> [CLIENTE] (Simulando perda de mensagem: {message})")

    msg = f"{flag}|{message}|{seq}"
    
    while True:
        try:
            sock.send(msg.encode('utf-8'))
            
            sock.settimeout(RETRANSMISSION_TIMEOUT)
            
            #Recebendo resposta do servidor
            resposta = sock.recv(1024).decode('utf-8')
            # recv : recebe dados de um socket conectado 
            sock.settimeout(None)
            
            print(f">> [CLIENTE] Resposta do servidor:{resposta}")

            if "ACK" in resposta:
                return seq + 1 # Sucesso, próximo número de sequência
            else:
                # Se for NACK sem ACK, retransmite
                print(">> [CLIENTE] NACK recebido. Retransmitindo...")

        except socket.timeout:
            print(f"\n>> [CLIENTE] TIMEOUT! Retransmitindo: {msg}")
        except Exception as e:
            print(f"Erro de socket na comunicação: {e}")
            raise e


def main():
    try:
        # metodo socket : cria um objeto socket TCP
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # método conect : cria uma conexão entre o servidor e o cliente no lado do cliente . Nesse caso uma conexão está sendo aberta na porta
        sock.connect(('localhost', 1500))
        
    except ConnectionRefusedError as error:
        print(f">> [CLIENTE] Aconteceu um erro ao tentar conectar ao servidor: {error}")
        print("Encerrando o programa...")
        
    else:
        try:
            # Realiza o handshake com o servidor
            handshake(sock)

            #Troca de mensagem com o Servidor
            seq = random.randint(0, 255)

            while True:
                #recebendo tamanho da janela do servidor
                sock.settimeout(None)
                resposta = sock.recv(1024).decode('utf-8')

                tamanho_janela = 0

                #modificando para inteiro o tamanho da janela com try catch
                try:
                    tamanho_janela = int(resposta)
                    print(f"\n>> [CLIENTE] Tamanho da janela do servidor recebido: {tamanho_janela}")
                except ValueError:
                    print(f">> [CLIENTE] Erro ao receber o tamanho da janela: {resposta}")

                if tamanho_janela == 0:
                    print("Tamanho da janela é 0, esperando atualização...")
                    continue
                    
                for i in range(tamanho_janela):
                    #Recebendo mensagem do cliente
                    message = input(f"\nDigite sua mensagem [{i+1}/{tamanho_janela}]: ")

                    #Enviando mensagem para o servidor
                    seq = comunicacao_server(sock, message, seq)

                #opção de sair apos a rajada com um input
                sair = input("\nDigite 'sair' para encerrar a conexão ou pressione Enter para continuar...")
                if sair.lower() == 'sair':
                    print("Desconectando do servidor...")
                    break
                    
        except Exception as e:
            print(f"\n>> [CLIENTE] Erro na comunicação: {e}")
            
        finally:
            # Fecha a conexão
            sock.close()
            print(">> [CLIENTE] Conexão fechada.")

if __name__ == "__main__":
    main()
