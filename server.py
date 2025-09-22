import socket

def print_titulo(texto):
    print("\n" + "=" * 80)
    print(f"{texto.center(80)}")
    print("=" * 80 + "\n")

def process_handshake(sock_client):
    print_titulo("AGUARDANDO HANDSHAKE DO CLIENTE")

    #1. Recebendo o SYN do cliente
    print(">> [SERVIDOR] Recebendo SYN do cliente...")
    resposta_syn = sock_client.recv(1024).decode('utf-8')
    print(f">> [SERVIDOR] SYN recebido: {resposta_syn}")

    #Confere o Handshake e separa o modo de operação e o tamanho máximo
    parts = resposta_syn.split('|')
    if parts[0] == "SYN" and len(parts) == 3:
        modo = parts[1]  
        tam_max = int(parts[2])  
        
        
        #2. Envia SYN-ACK para o cliente
        mensagem_syn_ack = f"SYN-ACK|{modo}|{tam_max}"
        print(f"\n>> [SERVIDOR] Enviando SYN-ACK para o cliente: {mensagem_syn_ack}")
        sock_client.send(mensagem_syn_ack.encode('utf-8'))

        #3. Recebendo ACK
        print("\n>> [SERVIDOR] Aguardando ACK...")
        resposta_ack = sock_client.recv(1024).decode('utf-8')
        print(">> [SERVIDOR] ACK recebido")

        if "ACK" == resposta_ack.split("|")[0]:
            print_titulo("HANDSHAKE DE 3 VIAS COMPLETO")
            return modo, tam_max
        else:
            print(">> [SERVIDOR] ERRO: ACK não recebido corretamente.")
            return None, None
    else:
        sock_client.send("Erro no handshake\n".encode('utf-8'))
        print(">> [SERVIDOR] ERRO: Formato de SYN inválido.")
        return None, None

#Recebendo mesnagens cliente
def comunicacao_cliente(sock_client):
    while True:
        print("\nAguardando mensagem do Client...")
        #Recebe a mensagem do cliente
        data = sock_client.recv(1024).decode('utf-8')
        #Se estiver vazia(o que indica que o cliente se  desconectou ), encerra a conexão
        if not data:
            break
        print("Mensagem recebida:", data)

        #Verifica o tipo da mensagem e responde
        parts = data.split('|')
        if parts[0] == "MSG":
            resposta = "RESPONSE|Mensagem recebida com sucesso!"
            sock_client.send(resposta.encode('utf-8'))
        elif parts[0] == "NACK":
            # o pacote foi enviado mas houve erro no pacote 
            resposta = "NACK|Erro no pacote"
            # pedindo a mensagem novamente com send 

            sock_client.send(resposta.encode('utf-8'))
        else:
            # o caso de não houver nack ou de não voltar a mensagem 
            resposta = "NACK|Formato de mensagem inválido"
            # pedindo a mensagem novamente com send 
            sock_client.send(resposta.encode('utf-8'))
    print("Cliente desconectado!")


def main():
    # cria um objeto socket TCP
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    sock.bind(('localhost', 1500))
     ## Set socket option to reuse address (helps avoid "Address already in use" errors
    # configura as opções do socket para reutilizar o endereço (ajuda a evitar ,mensagens de erro como : "endereço já está em uso ")
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.listen(1)
    print(f"\n>> [SERVIDOR] Ouvindo em localhost 1500")

    #Aceitando conexão com o cliente
    sock_client, endereco = sock.accept()

    #Realiza o handshake
    modo, tam_max = process_handshake(sock_client)
    print(f">> [SERVIDOR] Cliente de endereço: {endereco}, conectado!")

    if modo and tam_max:
        print(f">> [SERVIDOR] Modo de operação: {modo}, Tamanho máximo de pacote: {tam_max}")
        #Inicia a troca de mensagens
        comunicacao_cliente(sock_client)

    sock.close()
    
if __name__ == "__main__":
    main()
