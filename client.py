import socket

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

def comunicacao_server(sock, message):
    #Enviando mensagem ao servidor
    msg = f"MSG|{message}"
    sock.send(msg.encode('utf-8'))

    #Recebendo resposta do servidor
    resposta = sock.recv(1024).decode('utf-8')
    # recv : recebe dados de um socket conectado 
    print(f">> [CLIENTE] Resposta do servidor:{resposta}")

def main():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # metodo socket : cria um objeto socket TCP
        sock.connect(('localhost', 1500))
       # método conect : cria uma conexão entre o servidor e o cliente no lado do cliente . Nesse caso uma conexão está sendo aberta na porta
    except ConnectionRefusedError as error:
        print(f">> [CLIENTE] Aconteceu um erro ao tentar conectar ao servidor: {error}")
        print("Encerrando o programa...")
    else:
        # Realiza o handshake com o servidor
        handshake(sock)

        #Troca de mensagem com o Servidor

        while True:

            #recebendo tamanho da janela do servidor
            resposta = sock.recv(1024).decode('utf-8')

            tamanho_janela = 0

            #modificando para inteiro o tamanho da janela com try catch
            try:
                tamanho_janela = int(resposta)
                print(f">> [CLIENTE] Tamanho da janela do servidor recebido: {tamanho_janela}")
            except ValueError:
                print(f">> [CLIENTE] Erro ao receber o tamanho da janela: {resposta}")

            for i in range(tamanho_janela):
                #Recebendo mensagem do cliente
                message = input("\nDigite sua mensagem")

                #Enviando mensagem para o servidor
                comunicacao_server(sock, message)

            if tamanho_janela == 0:
                print("Tamanho da janela é 0, esperando atualização...")
                continue

            #opção de sair apos a rajada com um input
            sair = input("Digite 'sair' para encerrar a conexão ou pressione Enter para continuar...")
            if sair.lower() == 'sair':
                print("Desconectando do servidor...")
                break
            
    finally:
        # Fecha a conexão
        sock.close()

if __name__ == "__main__":
    main()

