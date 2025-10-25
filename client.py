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
    
    
    msg = f"{flag}|{message}|{seq}"
    
    try:
        sock.send(msg.encode('utf-8'))
        
      
        
        #Recebendo resposta do servidor
        resposta = sock.recv(1024).decode('utf-8')
        # recv : recebe dados de um socket conectado 
        
        
        print(f">> [CLIENTE] Resposta do servidor:{resposta}")

        if "ACK" in resposta and "NACK" not in resposta:
            return seq + 1 # Sucesso, próximo número de sequência
        else:
            # Se for NACK, retransmita o pacote
            print(">> [CLIENTE] NACK recebido. Retransmitindo...")
            sock.send(msg.encode('utf-8'))

    except socket.timeout:
        print("\n>> [CLIENTE] TIMER ESTOUROU") 
        print(f">> [CLIENTE] TIMEOUT! Retransmitindo: {msg}")
    except Exception as e:
        print(f"Erro de socket na comunicação: {e}")
        raise e

def enviar_janela(sock, pacotes, seq_inicial, tamanho_janela):
    seq = seq_inicial
    total_pacotes = len(pacotes)
    num = 0

    while num < total_pacotes:
        # Cria a janela atual
        janela = pacotes[num:num + tamanho_janela]
        print(f"\n>> [CLIENTE] Enviando janela {(num // tamanho_janela) + 1} com {len(janela)} pacotes...")

        # Envia todos os pacotes da janela
        for i, msg in enumerate(janela):
            flag = "MSG"
            pacote_msg = f"{flag}|{msg}|{seq + i}"
            print(f">> [CLIENTE] Enviando pacote {num + i + 1}/{total_pacotes}: {msg}")
            sock.send(pacote_msg.encode('utf-8'))

        # Espera resposta do servidor após enviar toda a janela
        try:
            sock.settimeout(RETRANSMISSION_TIMEOUT)
            resposta = sock.recv(1024).decode('utf-8')
            print(f">> [CLIENTE] Resposta do servidor: {resposta}")

            if "ACK" in resposta and "NACK" not in resposta:
                seq += len(janela)
                num += tamanho_janela
            else:
                print(">> [CLIENTE] NACK recebido — retransmitindo janela atual...")
                # retransmite a mesma janela
                continue

        except socket.timeout:
            print("\n>> [CLIENTE] TIMEOUT — retransmitindo janela atual...")
            # retransmite a mesma janela (sem avançar)
            continue

    print("\n>> [CLIENTE] Todos os pacotes foram enviados com sucesso!")
    return seq


'''crie uma função que faça o seguinte:
- receber como parametro: tamanho maximo de caracteres por janela e a mensagem a ser enviada
- dividir a mensagem em partes de acordo com o tamanho maximo de caracteres por janela
- retornar uma lista com as partes da mensagem dividida'''
def dividir_mensagem(tamanho_maximo, mensagem):
    partes = []
    for i in range(0, len(mensagem), tamanho_maximo):
        partes.append(mensagem[i:i + tamanho_maximo])
    return partes


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
                #recebendo tamanho de pacotes por janela do servidor
                sock.settimeout(None)
                resposta = sock.recv(1024).decode('utf-8')

                #recebdendo tamanho maximo de caracteres por janela do servidor
                resposta_caracteres = sock.recv(1024).decode('utf-8')
                

                qnt_pacotes = 0

                #modificando para inteiro o tamanho da janela com try catch
                try:
                    qnt_pacotes = int(resposta)
                    print(f"\n>> [CLIENTE] Tamanho da janela do servidor recebido: {qnt_pacotes}")
                except ValueError:
                    print(f">> [CLIENTE] Erro ao receber o tamanho da janela: {resposta}")

                #modificando para inteiro o tamanho maximo de caracteres por janela com try catch
                try:
                    tamanho_caracteres = int(resposta_caracteres)
                    print(f">> [CLIENTE] Tamanho máximo de caracteres por janela do servidor recebido: {tamanho_caracteres}")
                except ValueError:
                    print(f">> [CLIENTE] Erro ao receber o tamanho máximo de caracteres por janela: {resposta_caracteres}")

                if qnt_pacotes == 0:
                    print("Tamanho da janela é 0, esperando atualização...")
                    continue

                if tamanho_caracteres == 0:
                    print("Tamanho máximo de caracteres por janela é 0, esperando atualização...")
                    continue

                # Lendo mensagem do usuário
                message = input(f"\nDigite sua mensagem: ")
                pacotes = dividir_mensagem(tamanho_caracteres, message)
                print(f">> [CLIENTE] Pacotes divididos: {pacotes}")

                # Envia a mensagem em janelas Go-Back-N
                seq = enviar_janela(sock, pacotes, seq, qnt_pacotes)

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
