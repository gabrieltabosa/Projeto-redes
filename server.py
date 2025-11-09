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

def enviar_ack_sr(sock_client, seq_num):
    """
    Envia um ACK individual para o protocolo Selective Repeat.
    """
    resposta = f"ACK-SR:{seq_num}"
    checksum_resp = calculate_checksum(resposta)
    resposta_full = f"{resposta}|{checksum_resp}\n"
    sock_client.send(resposta_full.encode('utf-8'))

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


# --- LÓGICA DO SERVIDOR (AGORA UM ROTEADOR) ---
def comunicacao_cliente(sock_client, modo): # <--- Aceita 'modo'

    # Loop Externo (por Mensagem)
    while True:
        try:
            sock_client.settimeout(INACTIVITY_TIMEOUT)
            
            # 1. Espera a configuração (Janela|Total|SeqInicial) ou SAIR
            print("\n>> [SERVIDOR] Aguardando configuração de mensagem do cliente...")
            config_data = sock_client.recv(1024).decode('utf-8')
            
            if not config_data:
                print(">> [SERVIDOR] Cliente desconectou.")
                break
                
            if config_data == "SAIR":
                print(">> [SERVIDOR] Cliente solicitou encerramento.")
                break

            # Processa a configuração
            try:
                parts = config_data.split('|')
                qnt_pacotes_janela = int(parts[0])
                total_pacotes_msg = int(parts[1])
            except (ValueError, IndexError):
                print(f">> [SERVIDOR] ERRO: Configuração inválida recebida: {config_data}")
                continue
                
            print(f">> [SERVIDOR] Config recebida: Janela={qnt_pacotes_janela}, Total={total_pacotes_msg}")
            
            # ==========================================================
            # ROTEADOR DE PROTOCOLO (GBN ou SR)
            # ==========================================================
            
            if modo == "GoBackN":
                print_titulo("MODO GO-BACK-N ATIVADO")
                
                # Variáveis de estado do GBN
                rec_seq = None 
                pacotes_recebidos_total = 0
                mensagem_completa = ""
                
                # Loop Interno (por Janela, até completar a Mensagem) - LÓGICA GBN
                while pacotes_recebidos_total < total_pacotes_msg:
                    
                    qnt_esperada_janela = min(qnt_pacotes_janela, total_pacotes_msg - pacotes_recebidos_total)
                    print(f"\n>> [GBN-SERV] Aguardando janela... (Esperando {qnt_esperada_janela} pacotes de {total_pacotes_msg} total)")
                    
                    pacotes_descartados = False
                    data_full = "" 
                    
                    # Loop de recebimento da Janela
                    for i in range(qnt_esperada_janela):
                        # Este recv pode falhar se o cliente não enviar o pacote (simulação de perda)
                        try:
                            data_full = sock_client.recv(1024).decode('utf-8')
                        except socket.timeout:
                            # Se um pacote não chegar, o próximo recv estoura.
                            # No GBN, estourar o timer *no cliente* é o que inicia a retransmissão,
                            # mas aqui estamos esperando ativamente. Se o cliente parou de enviar,
                            # tratamos como desconexão.
                            data_full = ""

                        if not data_full:
                            print(">> [GBN-SERV] Cliente desconectou/parou de enviar no meio da janela.")
                            pacotes_descartados = True
                            break 

                        if pacotes_descartados:
                            print(f">> [GBN-SERV] (Descartando pacote {i+1} da janela - base já corrompida)")
                            continue

                        is_valid, data_part = verify_checksum(data_full)
                        if not is_valid:
                            print(f">> [GBN-SERV] ERRO: Checksum inválido. Descartando pacote {i+1} e o resto da janela.")
                            pacotes_descartados = True
                            continue 

                        try:
                            parts_data = data_part.split('|')
                            flag = parts_data[0]
                            msg_data = parts_data[1]
                            seq_recebido = int(parts_data[2])
                        except (IndexError, ValueError):
                            print(f">> [GBN-SERV] ERRO: Pacote malformado. {data_part}")
                            pacotes_descartados = True
                            continue
                            
                        if rec_seq is None:
                            rec_seq = seq_recebido

                        if flag == "MSG" and seq_recebido == rec_seq:
                            print(f">> [GBN-SERV] Pacote {i+1} (SEQ={seq_recebido}) recebido com sucesso.")
                            mensagem_completa += msg_data
                            rec_seq += 1 
                        else:
                            # Pacote fora de ordem (GBN!), ou seja, o pacote rec_seq foi perdido/corrompido.
                            print(f">> [GBN-SERV] ERRO: Pacote inesperado (Flag:{flag}, Esperado_SEQ:{rec_seq}, Recebido_SEQ:{seq_recebido})")
                            print(f">> [GBN-SERV] Descartando pacote {i+1} e o resto da janela.")
                            pacotes_descartados = True
                            continue 

                    # Fim do loop 'for' (fim da janela GBN)
                    if not data_full and pacotes_descartados:
                        break
                    
                    ack_response = rec_seq if rec_seq is not None else 0

                    if pacotes_descartados:
                        # Envia NACK:N, onde N é o pacote que *esperamos* (rec_seq)
                        resposta = f"NACK:{ack_response}"
                        print(f">> [GBN-SERV] Janela falhou. Enviando NACK para {ack_response}.")
                    else:
                        # Envia ACK:N, onde N é o próximo pacote *esperado* (rec_seq)
                        resposta = f"ACK:{ack_response}"
                        print(f">> [GBN-SERV] Janela recebida com sucesso. Enviando ACK cumulativo: {ack_response}.")
                        pacotes_recebidos_total += qnt_esperada_janela
                    
                    checksum_resp = calculate_checksum(resposta)
                    resposta_full = f"{resposta}|{checksum_resp}"
                    sock_client.send(resposta_full.encode('utf-8'))

                # Fim do loop 'while' (fim da mensagem GBN)
                if pacotes_recebidos_total == total_pacotes_msg:
                    print(f"\n>> [SERVIDOR] Mensagem completa (GBN) recebida: '{mensagem_completa}'")

            elif modo == "RepetiçãoSeletiva":
                print_titulo("MODO REPETIÇÃO SELETIVA ATIVADO")
                try:
                    # Pega o SEQ inicial da configuração (parts[2])
                    rec_seq_inicial = int(parts[2]) 
                    print(f">> [SR-SERV] Base de sequência inicial esperada: {rec_seq_inicial}")
                except (ValueError, IndexError):
                    print(f">> [SERVIDOR] ERRO: Config SR não incluiu SEQ inicial. {config_data}")
                    continue # Volta ao loop de esperar config
                
                # Chama a função SR (ela agora faz todo o trabalho)
                comunicacao_cliente_sr(sock_client, 
                                       qnt_pacotes_janela, 
                                       total_pacotes_msg, 
                                       rec_seq_inicial)

        except socket.timeout:
            print(f"\n>> [SERVIDOR] ERRO: Cliente inativo por {INACTIVITY_TIMEOUT}s. Encerrando.")
            break
        except Exception as e:
            print(f"\n>> [SERVIDOR] ERRO na comunicação: {e}. Encerrando conexão.")
            break

    print(">> [SERVIDOR] Cliente desconectado!")

# --- LÓGICA DO SERVIDOR SELECTIVE REPEAT ---
def comunicacao_cliente_sr(sock_client, qnt_pacotes_janela, total_pacotes_msg, rec_seq_inicial):
    
    print(f"\n>> [SR-SERV] Aguardando {total_pacotes_msg} pacotes (Janela={qnt_pacotes_janela}, Base={rec_seq_inicial})")
    
    rec_seq = rec_seq_inicial      # O próximo pacote esperado (base da janela)
    pacotes_recebidos_total = 0 # Contador de pacotes entregues à aplicação
    mensagem_completa = ""
    
    # Buffer para pacotes fora de ordem (mas dentro da janela)
    buffer_recebimento = {} # Formato: {seq_num: data}

    while pacotes_recebidos_total < total_pacotes_msg:
        try:
            sock_client.settimeout(INACTIVITY_TIMEOUT)
            data_full = sock_client.recv(1024).decode('utf-8')
            
            if not data_full:
                print(">> [SR-SERV] Cliente desconectou inesperadamente.")
                return False

            # Verifica Checksum
            is_valid, data_part = verify_checksum(data_full)
            if not is_valid:
                print(f">> [SR-SERV] ERRO: Checksum inválido. Descartando pacote (Descarte Passivo).")
                continue # SR: Apenas descarta, não afeta os outros

            # Processa o pacote válido
            try:
                parts = data_part.split('|')
                flag = parts[0]
                msg_data = parts[1]
                seq_recebido = int(parts[2])
            except (IndexError, ValueError):
                print(f">> [SR-SERV] ERRO: Pacote malformado. {data_part}")
                continue

            if flag != "MSG":
                print(f">> [SR-SERV] Pacote não é MSG, ignorando: {flag}")
                continue

            # --- LÓGICA CENTRAL SR ---

            # 1. Pacote já foi recebido e entregue (ACK pode ter sido perdido)
            if seq_recebido < rec_seq:
                print(f">> [SR-SERV] Pacote duplicado (SEQ={seq_recebido}) recebido. Reenviando ACK.")
                enviar_ack_sr(sock_client, seq_recebido)
                continue

            # 2. Pacote está DENTRO da janela de recebimento
            if rec_seq <= seq_recebido < (rec_seq + qnt_pacotes_janela):
                
                print(f">> [SR-SERV] Pacote (SEQ={seq_recebido}) recebido. Enviando ACK-SR.")
                enviar_ack_sr(sock_client, seq_recebido) # Envia ACK individual
                
                # 2a. É o pacote esperado!
                if seq_recebido == rec_seq:
                    print(f">> [SR-SERV] Pacote {seq_recebido} (base) aceito.")
                    mensagem_completa += msg_data
                    pacotes_recebidos_total += 1
                    rec_seq += 1 # Desliza a base

                    # Agora, verifica o buffer para entregar pacotes contíguos
                    while rec_seq in buffer_recebimento:
                        print(f">> [SR-SERV] Entregando pacote {rec_seq} do buffer.")
                        data_buffer = buffer_recebimento.pop(rec_seq)
                        mensagem_completa += data_buffer
                        pacotes_recebidos_total += 1
                        rec_seq += 1 # Desliza a base novamente
                    
                    print(f">> [SR-SERV] Nova base: {rec_seq}")

                # 2b. É fora de ordem, mas na janela. Bufferiza.
                else:
                    if seq_recebido not in buffer_recebimento:
                        print(f">> [SR-SERV] Pacote {seq_recebido} (fora de ordem) bufferizado.")
                        buffer_recebimento[seq_recebido] = msg_data
                    else:
                        print(f">> [SR-SERV] Pacote {seq_recebido} (bufferizado) duplicado. ACK reenviado.")

            # 3. Pacote fora da janela (muito adiantado)
            else:
                print(f">> [SR-SERV] ERRO: Pacote {seq_recebido} fora da janela (Base={rec_seq}, Janela={qnt_pacotes_janela}). Descartado.")
                # Nota: Não enviamos NACK, apenas ignoramos.
                # O cliente vai estourar o timer eventualmente se o pacote foi perdido.

        except socket.timeout:
            print(f"\n>> [SR-SERV] ERRO: Cliente inativo por {INACTIVITY_TIMEOUT}s. Encerrando.")
            return False
        except Exception as e:
            print(f"\n>> [SR-SERV] ERRO na comunicação: {e}. Encerrando conexão.")
            return False

    print(f"\n>> [SERVIDOR] Mensagem completa (SR) recebida: '{mensagem_completa}'")
    return True


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
        modo, tam_max = process_handshake(sock_client) # <--- 'modo' já é retornado aqui
        print(f">> [SERVIDOR] Cliente de endereço: {endereco}, conectado!")

        if modo and tam_max:
            print(f">> [SERVIDOR] Modo de operação: {modo}, Tamanho máximo de pacote: {tam_max}")
            #Inicia a troca de mensagens
            comunicacao_cliente(sock_client, modo)  

        sock_client.close()

    except Exception as e:
        print(f"Erro principal no servidor: {e}")
    finally:
        sock.close()
        print(">> [SERVIDOR] Servidor encerrado.")

if __name__ == "__main__":
    main()