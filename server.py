import socket
import random

HANDSHAKE_TIMEOUT = 10.0
INACTIVITY_TIMEOUT = 300.0 # Aumentado para longas transferências

# ==============================================================================
# FUNÇÕES AUXILIARES (Impressão e Checksum)
# ==============================================================================

def print_titulo(texto):
    print("\n" + "=" * 80)
    print(f"{texto.center(80)}")
    print("=" * 80 + "\n")

def calculate_checksum(data_str: str) -> int:
    """
    Calcula um checksum simples de soma de 16 bits.
    """
    checksum = 0
    for char in data_str:
        # Soma o valor ASCII/UTF-8 de cada caractere
        checksum += ord(char)
    # Garante que o resultado esteja dentro de 16 bits (0-65535)
    return checksum % 65536 

def verify_checksum(full_packet: str) -> (bool, str):
    """
    Verifica o checksum de um pacote completo.
    Retorna (True, data_part) se válido, ou (False, None) se inválido.
    """
    try:
        # Divide o pacote na última ocorrência de '|'
        data_part, received_checksum_str = full_packet.rsplit('|', 1)
        received_checksum = int(received_checksum_str)
        
        # Recalcula o checksum com base na parte dos dados
        calculated_checksum = calculate_checksum(data_part)
        
        if received_checksum == calculated_checksum:
            return (True, data_part)  # Checksum OK
        else:
            return (False, None) # Checksum falhou
            
    except (ValueError, IndexError):
        # Ocorreu um erro se o pacote não tiver '|' ou o checksum não for um número
        return (False, None) # Pacote malformado

# ==============================================================================
# LÓGICA DO PROTOCOLO (Handshake e Comunicação GBN)
# ==============================================================================

def process_handshake(sock_client):
    print_titulo("AGUARDANDO HANDSHAKE DO CLIENTE")

    try:
        #1. Recebendo o SYN do cliente
        print(">> [SERVIDOR] Recebendo SYN do cliente...")
        sock_client.settimeout(HANDSHAKE_TIMEOUT)
        resposta_syn_full = sock_client.recv(1024).decode('utf-8')
        sock_client.settimeout(None)

        # Verifica checksum do SYN
        is_valid, resposta_syn = verify_checksum(resposta_syn_full)
        if not is_valid:
            print(f">> [SERVIDOR] ERRO: Checksum do SYN inválido: {resposta_syn_full}")
            return None, None
            
        print(f">> [SERVIDOR] SYN (checksum OK) recebido: {resposta_syn_full}")

        #Confere o Handshake (usando resposta_syn verificado)
        parts = resposta_syn.split('|')
        if parts[0] == "SYN" and len(parts) == 3:
            modo = parts[1]
            tam_max = int(parts[2])

            #2. Envia SYN-ACK para o cliente
            # Adiciona checksum
            data_syn_ack = f"SYN-ACK|{modo}|{tam_max}"
            checksum_syn_ack = calculate_checksum(data_syn_ack)
            mensagem_syn_ack = f"{data_syn_ack}|{checksum_syn_ack}"
            
            print(f"\n>> [SERVIDOR] Enviando SYN-ACK para o cliente: {mensagem_syn_ack}")
            sock_client.send(mensagem_syn_ack.encode('utf-8'))

            #3. Recebendo ACK
            print("\n>> [SERVIDOR] Aguardando ACK...")
            sock_client.settimeout(HANDSHAKE_TIMEOUT)
            resposta_ack_full = sock_client.recv(1024).decode('utf-8')
            sock_client.settimeout(None)

            # Verifica checksum do ACK
            is_valid_ack, data_ack = verify_checksum(resposta_ack_full)
            if not is_valid_ack:
                print(f">> [SERVIDOR] ERRO: Checksum do ACK inválido: {resposta_ack_full}")
                return None, None

            print(">> [SERVIDOR] ACK (checksum OK) recebido")

            if "ACK" == data_ack.split("|")[0]:
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


# --- NOVA LÓGICA DE SERVIDOR GO-BACK-N ---
def comunicacao_cliente(sock_client):

    rec_seq = None # Número de sequência esperado
    mensagem_completa = ""

    while True:
        try:
            sock_client.settimeout(INACTIVITY_TIMEOUT)
            
            # 1. Espera a configuração da janela do cliente
            print("\n>> [SERVIDOR] Aguardando configuração de janela do cliente...")
            config_data = sock_client.recv(1024).decode('utf-8')
            
            if not config_data:
                print(">> [SERVIDOR] Cliente desconectou antes de configurar a janela.")
                break
                
            if config_data == "SAIR":
                print(">> [SERVIDOR] Cliente solicitou encerramento.")
                break

            qnt_pacotes = int(config_data)
            print(f">> [SERVIDOR] Configuração recebida: esperando {qnt_pacotes} pacotes.")

            pacotes_descartados = False
            ack_response = rec_seq if rec_seq is not None else 0

            # 2. Loop para receber a janela inteira
            for i in range(qnt_pacotes):
                print(f">> [SERVIDOR] Aguardando pacote {i+1}/{qnt_pacotes}...")
                data_full = sock_client.recv(1024).decode('utf-8')
                
                if not data_full:
                    print(">> [SERVIDOR] Cliente desconectou no meio da janela.")
                    pacotes_descartados = True
                    break

                # Se já encontramos um erro, apenas consumimos o resto da janela do buffer
                if pacotes_descartados:
                    print(f">> [SERVIDOR] (Descartando pacote {i+1} - janela já corrompida)")
                    continue

                # Verifica Checksum
                is_valid, data_part = verify_checksum(data_full)
                if not is_valid:
                    print(f">> [SERVIDOR] ERRO: Checksum inválido. Descartando pacote {i+1} e o resto da janela.")
                    pacotes_descartados = True
                    continue # Começa a descartar

                # Processa o pacote válido
                parts = data_part.split('|')
                flag = parts[0]
                msg_data = parts[1]
                seq_recebido = int(parts[2])

                # Inicializa o número de sequência esperado no primeiro pacote
                if rec_seq is None:
                    rec_seq = seq_recebido

                # Verifica a ordem (Lógica GBN)
                if flag == "MSG" and seq_recebido == rec_seq:
                    # Pacote esperado! Aceita.
                    print(f">> [SERVIDOR] Pacote {i+1} (SEQ={seq_recebido}) recebido com sucesso.")
                    mensagem_completa += msg_data
                    rec_seq += 1
                else:
                    # Pacote fora de ordem, duplicado ou corrompido (flag != MSG)
                    print(f">> [SERVIDOR] ERRO: Pacote fora de ordem. (Esperado: {rec_seq}, Recebido: {seq_recebido})")
                    print(f">> [SERVIDOR] Descartando pacote {i+1} e o resto da janela.")
                    pacotes_descartados = True
                    continue # Começa a descartar

            # 3. Envia resposta CUMULATIVA (ACK ou NACK)
            ack_response = rec_seq if rec_seq is not None else 0 # O ACK é sempre o *próximo* esperado

            if pacotes_descartados:
                resposta = f"NACK:{ack_response}"
                print(f">> [SERVIDOR] Janela falhou. Enviando NACK para {ack_response}.")
            else:
                resposta = f"ACK:{ack_response}"
                print(f">> [SERVIDOR] Janela recebida com sucesso. Enviando ACK cumulativo: {ack_response}.")
                print(f"   >> Mensagem até agora: '{mensagem_completa}'")
                
            # Adiciona checksum à resposta
            checksum_resp = calculate_checksum(resposta)
            resposta_full = f"{resposta}|{checksum_resp}"
            sock_client.send(resposta_full.encode('utf-8'))

        except socket.timeout:
            print(f"\n>> [SERVIDOR] ERRO: Cliente inativo por {INACTIVITY_TIMEOUT}s. Encerrando.")
            break
        except Exception as e:
            print(f"\n>> [SERVIDOR] ERRO na comunicação: {e}. Encerrando conexão.")
            break

    print(f"\n>> [SERVIDOR] Mensagem final recebida: '{mensagem_completa}'")
    print(">> [SERVIDOR] Cliente desconectado!")


def main():
    try:
        # cria um objeto socket TCP
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        sock.bind(('localhost', 1500))
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
            #Inicia a troca de mensagens (agora com lógica GBN)
            comunicacao_cliente(sock_client)

        sock_client.close()

    except Exception as e:
        print(f"Erro principal no servidor: {e}")
    finally:
        sock.close()
        print(">> [SERVIDOR] Servidor encerrado.")

if __name__ == "__main__":
    main()