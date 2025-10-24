import socket
import random

HANDSHAKE_TIMEOUT = 10.0
INACTIVITY_TIMEOUT = 60.0

def print_titulo(texto):
    print("\n" + "=" * 80)
    print(f"{texto.center(80)}")
    print("=" * 80 + "\n")

def process_handshake(sock_client):
    print_titulo("AGUARDANDO HANDSHAKE DO CLIENTE")

    try:
        #1. Recebendo o SYN do cliente
        print(">> [SERVIDOR] Recebendo SYN do cliente...")
        sock_client.settimeout(HANDSHAKE_TIMEOUT)
        resposta_syn = sock_client.recv(1024).decode('utf-8')
        sock_client.settimeout(None)
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
            sock_client.settimeout(HANDSHAKE_TIMEOUT)
            resposta_ack = sock_client.recv(1024).decode('utf-8')
            sock_client.settimeout(None)
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
            
    except socket.timeout:
        print("\n>> [SERVIDOR] TIMER ESTOUROU") 
        print(f">> [SERVIDOR] ERRO: Timeout no handshake")
        return None, None
    except Exception as e:
        print(f"\n>> [SERVIDOR] ERRO inesperado no handshake: {e}")
        return None, None


#recebendo mesnagens cliente
def comunicacao_cliente(sock_client):
    tamanho_janela = 5
    print(f">> [SERVIDOR] Enviando tamanho da janela para o cliente: {tamanho_janela}")
    sock_client.send(str(tamanho_janela).encode('utf-8'))

    rec = None 

    while True:
        try:
            print("\nAguardando mensagem do Client...")
            sock_client.settimeout(INACTIVITY_TIMEOUT)
            #recebe a mensagem do cliente
            data = sock_client.recv(1024).decode('utf-8')
            sock_client.settimeout(None)
            
            #se estiver vazia(o que indica que o cliente se desconectou ), encerra a conexão
            if not data:
                print(">> [SERVIDOR] Cliente encerrou a conexão.")
                break
            print("Mensagem recebida:", data)

            parts = data.split('|')
            resposta = ""
            
            # tenta extrair a flag e o número de sequência
            if len(parts) < 3:
                 flag = parts[0]
                 seq_recebido = -1
            else:
                 flag = parts[0]
                 try:
                    seq_recebido = int(parts[2])
                 except ValueError:
                    seq_recebido = -1

            # inicializa 'rec' com o primeiro pacote MSG que chega
            if rec is None and flag == "MSG" and seq_recebido >= 0:
                 rec = seq_recebido
            
            # define o valor de ACK para a resposta
            ack_response = rec if rec is not None else 0 

            #caso a mensagem seja do tipo MSG, verifique o seq, incremente o numero de reconhecimento e envie um ACK. Se for Perda, não atualize o numero de reconhecimento e envie um ACK
            if flag == "MSG":
                if seq_recebido == rec:
                    # pacote esperado, incrementa o reconhecimento.
                    rec += 1
                    ack_response = rec # o ACK agora aponta para o próximo (rec+1)
                    mensagem_status = "Mensagem recebida com sucesso!"
                elif seq_recebido < rec and seq_recebido >= 0:
                    # pacote duplicado (reenvio). Apenas reenviamos o ACK anterior (o 'rec' atual).
                    mensagem_status = f"Mensagem duplicada (seq={seq_recebido}). ACK reenviado."
                else:
                    # pacote fora de ordem (só acontece em modos GBN/SR)
                    mensagem_status = f"Pacote fora de ordem (Esperado: {rec}, Recebido: {seq_recebido})."

                # modifique a string resposta e adicione um '\n' com o ACK em seguida
                resposta = f"RESPONSE|{mensagem_status}\nACK:{ack_response}"

                sock_client.send(resposta.encode('utf-8'))
                
            elif flag == "PERDA":
                # se for perda, não atualize o numero de reconhecimento e envie um ACK
                resposta = "NACK|Mensagem perdida, por favor reenvie\n" \
                f"ACK:{ack_response}" # Usa o rec atual

                sock_client.send(resposta.encode('utf-8'))
                
            elif flag == "NACK":
                resposta = "NACK|Erro no pacote"
                sock_client.send(resposta.encode('utf-8'))
                
            else:
                # o caso de não houver nack ou de não voltar a mensagem
                resposta = "NACK|Formato de mensagem inválido"
                sock_client.send(resposta.encode('utf-8'))

            # A lógica de janela só deve decrementar se um pacote NOVO for aceito
            if flag == "MSG" and seq_recebido == rec - 1:
                tamanho_janela -= 1

            if (tamanho_janela <= 0):
                print("\nJanela cheia. Redefinindo a janela...\n")
                #define a janela por um numero aleatorio entre 1 e 5 e envie pro servidor
                tamanho_janela = random.randint(1,5)
                print(f">> [SERVIDOR] Enviando tamanho da janela para o cliente: {tamanho_janela}")
                sock_client.send(str(tamanho_janela).encode('utf-8'))

        except socket.timeout:
            print("\n>> [SERVIDOR] TIMER ESTOUROU") 
            print(f">> [SERVIDOR] ERRO: Cliente inativo. Encerrando conexão.")
            break
        except Exception as e:
            print(f"\n>> [SERVIDOR] ERRO na comunicação: {e}. Encerrando conexão.")
            break

    print("Cliente desconectado!")


def main():
    try:
        # cria um objeto socket TCP
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        sock.bind(('localhost', 1500))
        ## Set socket option to reuse address (helps avoid "Address already in use" errors)
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

        sock_client.close()

    except Exception as e:
        print(f"Erro principal no servidor: {e}")
    finally:
        sock.close()
        print(">> [SERVIDOR] Servidor encerrado.")

if __name__ == "__main__":
    main()