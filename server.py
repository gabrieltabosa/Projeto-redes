import random
import socket
from security import SecurityManager

HANDSHAKE_TIMEOUT = 10.0
INACTIVITY_TIMEOUT = 300.0 
# REDUZIDO PARA 0.5s: Servidor deve detectar perda rápido para não travar o cliente
WINDOW_RECEIVE_TIMEOUT = 0.5 

# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================

def print_titulo(texto):
    print("\n" + "=" * 80)
    print(f"{texto.center(80)}")
    print("=" * 80 + "\n")

def calculate_checksum(data_str: str) -> int:
    checksum = 0
    for char in data_str:
        checksum += ord(char)
    return checksum % 65536 

def verify_checksum(full_packet: str) -> (bool, str):
    try:
        data_part, received_checksum_str = full_packet.rsplit('|', 1)
        received_checksum = int(received_checksum_str)
        calculated_checksum = calculate_checksum(data_part)
        
        if received_checksum == calculated_checksum:
            return (True, data_part)  
        else:
            return (False, None) 
            
    except (ValueError, IndexError):
        return (False, None)

# ==============================================================================
# LÓGICA DO PROTOCOLO
# ==============================================================================

def enviar_ack_sr(sock_client, seq_num):
    resposta = f"ACK-SR:{seq_num}"
    checksum_resp = calculate_checksum(resposta)
    resposta_full = f"{resposta}|{checksum_resp}\n"
    sock_client.send(resposta_full.encode('utf-8'))

def process_handshake(sock_client):
    print_titulo("AGUARDANDO HANDSHAKE DO CLIENTE")

    try:
        print(">> [SERVIDOR] Recebendo SYN do cliente...")
        sock_client.settimeout(HANDSHAKE_TIMEOUT)
        resposta_syn_full = sock_client.recv(1024).decode('utf-8')
        sock_client.settimeout(None)

        is_valid, resposta_syn = verify_checksum(resposta_syn_full)
        if not is_valid:
            print(f">> [SERVIDOR] ERRO: Checksum do SYN inválido: {resposta_syn_full}")
            return None, None
            
        print(f">> [SERVIDOR] SYN (checksum OK) recebido: {resposta_syn_full}")

        parts = resposta_syn.split('|')
        if parts[0] == "SYN" and len(parts) == 3:
            modo = parts[1]
            tam_max = int(parts[2])

            data_syn_ack = f"SYN-ACK|{modo}|{tam_max}"
            checksum_syn_ack = calculate_checksum(data_syn_ack)
            mensagem_syn_ack = f"{data_syn_ack}|{checksum_syn_ack}"
            
            print(f"\n>> [SERVIDOR] Enviando SYN-ACK para o cliente: {mensagem_syn_ack}")
            sock_client.send(mensagem_syn_ack.encode('utf-8'))

            print("\n>> [SERVIDOR] Aguardando ACK...")
            sock_client.settimeout(HANDSHAKE_TIMEOUT)
            resposta_ack_full = sock_client.recv(1024).decode('utf-8')
            sock_client.settimeout(None)

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
            
    except (socket.timeout, TimeoutError):
        print("\n>> [SERVIDOR] TIMER ESTOUROU") 
        print(f">> [SERVIDOR] ERRO: Timeout no handshake")
        return None, None
    except Exception as e:
        print(f"\n>> [SERVIDOR] ERRO inesperado no handshake: {e}")
        return None, None


# --- LÓGICA DO SERVIDOR (COM SEGURANÇA) ---
def comunicacao_cliente(sock_client, modo, seguranca): 

    # BUFFER GLOBAL PARA O SERVIDOR LIDAR COM COLAGEM DE PACOTES
    buffer_entrada = ""

    while True:
        try:
            # Timeout longo padrão para inatividade geral
            sock_client.settimeout(INACTIVITY_TIMEOUT)
            
            print("\n>> [SERVIDOR] Aguardando configuração de mensagem do cliente...")
            try:
                # Recebendo a mensagem de configuração completa (incluindo checksum)
                config_full = sock_client.recv(1024).decode('utf-8').strip()
            except (socket.timeout, TimeoutError):
                continue 
            
            if not config_full:
                print(">> [SERVIDOR] Cliente desconectou.")
                break
                
            if config_full == "SAIR":
                print(">> [SERVIDOR] Cliente solicitou encerramento.")
                break

            # NOVO: Verificar o checksum da mensagem de configuração
            is_valid_config, config_data = verify_checksum(config_full)
            if not is_valid_config:
                print(f">> [SERVIDOR] ERRO: Checksum da Configuração inválido: {config_full}")
                continue # Pula para a próxima iteração do loop (aguarda reenvio, se o cliente fizer)
            
            try:
                # Extraindo os dados da configuração (agora 'config_data' sem o checksum)
                parts = config_data.split('|')
                # A linha de código original foi: parts = config_data.split('|'), então removemos a linha config_data = sock_client.recv(1024).decode('utf-8')
                qnt_pacotes_janela = int(parts[0])
                total_pacotes_msg = int(parts[1])
                seq_inicial_msg = int(parts[2].strip()) 
                
            except (ValueError, IndexError):
                print(f">> [SERVIDOR] ERRO: Configuração inválida recebida: {config_data}")
                continue
                
            print(f">> [SERVIDOR] Config (checksum OK) recebida: Janela={qnt_pacotes_janela}, Total={total_pacotes_msg}, Base={seq_inicial_msg}")
            
            if modo == "GoBackN":
                print_titulo("MODO GO-BACK-N ATIVADO")
                
                rec_seq = seq_inicial_msg
                pacotes_recebidos_total = 0
                mensagem_completa = ""
                
                # Limpa buffer para nova transmissão
                buffer_entrada = ""
                
                while pacotes_recebidos_total < total_pacotes_msg:
                    
                    qnt_esperada_janela = min(qnt_pacotes_janela, total_pacotes_msg - pacotes_recebidos_total)
                    print(f"\n>> [GBN-SERV] Aguardando janela... (Esperando {qnt_esperada_janela} pacotes)")
                    
                    pacotes_validos_na_janela = 0
                    
                    # Usa timeout curto para detectar perda rapidamente
                    sock_client.settimeout(WINDOW_RECEIVE_TIMEOUT)
                    
                    # Loop para consumir a quantidade de pacotes esperados
                    for i in range(qnt_esperada_janela):
                        
                        # --- LÓGICA DE BUFFER PARA SEPARAR PACOTES ---
                        try:
                            while '\n' not in buffer_entrada:
                                temp_data = sock_client.recv(2048).decode('utf-8')
                                if not temp_data: break
                                buffer_entrada += temp_data
                            
                            if '\n' in buffer_entrada:
                                data_full, buffer_entrada = buffer_entrada.split('\n', 1)
                            else:
                                data_full = "" # Timeout ou fim de stream sem newline
                                
                        except (socket.timeout, TimeoutError):
                            print(">> [GBN-SERV] Timeout: Cliente parou de enviar (provável perda simulada).")
                            data_full = ""
                            break 
                        # ---------------------------------------------

                        if not data_full:
                            print(">> [GBN-SERV] Sem dados completos (Timeout ou desconexão).")
                            break 

                        is_valid, data_part = verify_checksum(data_full)
                        if not is_valid:
                            print(f">> [GBN-SERV] Checksum inválido no pacote {i+1}. Ignorando.")
                            continue 

                        try:
                            parts_data = data_part.split('|')
                            flag = parts_data[0]
                            msg_data_encriptada = parts_data[1]
                            seq_recebido = int(parts_data[2])
                        except (IndexError, ValueError):
                            print(f">> [GBN-SERV] Pacote malformado. Ignorando.")
                            continue

                        if flag == "MSG":
                            if seq_recebido == rec_seq:
                                try:
                                    msg_original = seguranca.decrypt(msg_data_encriptada)
                                    print(f">> [GBN-SERV] Pacote aceito (SEQ={seq_recebido}): '{msg_original}'")
                                    mensagem_completa += msg_original
                                    rec_seq += 1 
                                    pacotes_validos_na_janela += 1
                                except Exception as e:
                                    print(f">> [GBN-SERV] ERRO SEGURANÇA: {e}")
                                    
                            elif seq_recebido < rec_seq:
                                print(f">> [GBN-SERV] Pacote duplicado (SEQ={seq_recebido}). Ignorando (Já temos).")
                            else:
                                print(f">> [GBN-SERV] Pacote fora de ordem (SEQ={seq_recebido}, Esperado={rec_seq}). Descartando.")
                        else:
                            print(f">> [GBN-SERV] Flag desconhecida: {flag}")

                    # Restaura timeout longo
                    sock_client.settimeout(INACTIVITY_TIMEOUT)
                    
                    # ACK cumulativo
                    ack_response = rec_seq
                    
                    if pacotes_validos_na_janela > 0:
                            pacotes_recebidos_total += pacotes_validos_na_janela
                            print(f">> [GBN-SERV] Janela processada. Enviando ACK cumulativo: {ack_response}")
                            resposta = f"ACK:{ack_response}"
                    else:
                            print(f">> [GBN-SERV] Janela sem progresso. Enviando NACK para {ack_response}")
                            resposta = f"NACK:{ack_response}"
                    
                    checksum_resp = calculate_checksum(resposta)
                    resposta_full = f"{resposta}|{checksum_resp}"
                    sock_client.send(resposta_full.encode('utf-8'))

                if pacotes_recebidos_total >= total_pacotes_msg:
                    print(f"\n>> [SERVIDOR] Mensagem completa (GBN) recebida: '{mensagem_completa}'")

            elif modo == "RepetiçãoSeletiva":
                print_titulo("MODO REPETIÇÃO SELETIVA ATIVADO")
                try:
                    rec_seq_inicial = seq_inicial_msg
                    print(f">> [SR-SERV] Base de sequência inicial esperada: {rec_seq_inicial}")
                except (ValueError, IndexError):
                    print(f">> [SERVIDOR] ERRO: Config SR não incluiu SEQ inicial. {config_data}")
                    continue 
                
                comunicacao_cliente_sr(sock_client, 
                                        qnt_pacotes_janela, 
                                        total_pacotes_msg, 
                                        rec_seq_inicial,
                                        seguranca)

        except (socket.timeout, TimeoutError):
            print(f"\n>> [SERVIDOR] ERRO: Cliente inativo por {INACTIVITY_TIMEOUT}s. Encerrando.")
            break
        except Exception as e:
            print(f"\n>> [SERVIDOR] ERRO CRÍTICO na comunicação: {e}. Encerrando conexão.")
            import traceback
            traceback.print_exc() 
            break

    print(">> [SERVIDOR] Cliente desconectado!")

# --- LÓGICA DO SERVIDOR SELECTIVE REPEAT (COM SEGURANÇA) ---
def comunicacao_cliente_sr(sock_client, qnt_pacotes_janela, total_pacotes_msg, rec_seq_inicial, seguranca):
    
    print(f"\n>> [SR-SERV] Aguardando {total_pacotes_msg} pacotes (Janela={qnt_pacotes_janela}, Base={rec_seq_inicial})")
    
    rec_seq = rec_seq_inicial       
    pacotes_recebidos_total = 0 
    mensagem_completa = ""
    
    buffer_recebimento = {} 
    buffer_entrada = ""

    while pacotes_recebidos_total < total_pacotes_msg:
        try:
            sock_client.settimeout(INACTIVITY_TIMEOUT)
            
            # --- LÓGICA DE BUFFER PARA SEPARAR PACOTES ---
            try:
                while '\n' not in buffer_entrada:
                    temp_data = sock_client.recv(2048).decode('utf-8')
                    if not temp_data: break
                    buffer_entrada += temp_data
                
                if '\n' in buffer_entrada:
                    data_full, buffer_entrada = buffer_entrada.split('\n', 1)
                else:
                    data_full = ""
            except Exception:
                data_full = ""
            # ---------------------------------------------

            if not data_full:
                print(">> [SR-SERV] Cliente desconectou ou erro de leitura.")
                return False

            is_valid, data_part = verify_checksum(data_full)
            if not is_valid:
                print(f">> [SR-SERV] Checksum inválido.")
                continue 

            try:
                parts = data_part.split('|')
                flag = parts[0]
                msg_data_encriptada = parts[1]
                seq_recebido = int(parts[2])
            except (IndexError, ValueError):
                continue

            if flag != "MSG":
                continue

            if seq_recebido < rec_seq:
                print(f">> [SR-SERV] Duplicado (SEQ={seq_recebido}). Reenviando ACK.")
                enviar_ack_sr(sock_client, seq_recebido)
                continue

            if rec_seq <= seq_recebido < (rec_seq + qnt_pacotes_janela):
                
                try:
                    msg_original = seguranca.decrypt(msg_data_encriptada)
                except Exception:
                    continue

                print(f">> [SR-SERV] Pacote (SEQ={seq_recebido}) recebido. Enviando ACK-SR.")
                enviar_ack_sr(sock_client, seq_recebido) 
                
                if seq_recebido == rec_seq:
                    mensagem_completa += msg_original
                    pacotes_recebidos_total += 1
                    rec_seq += 1 

                    while rec_seq in buffer_recebimento:
                        data_buffer = buffer_recebimento.pop(rec_seq)
                        mensagem_completa += data_buffer
                        pacotes_recebidos_total += 1
                        rec_seq += 1 
                else:
                    if seq_recebido not in buffer_recebimento:
                        buffer_recebimento[seq_recebido] = msg_original

        except (socket.timeout, TimeoutError):
            print(f"\n>> [SR-SERV] Inatividade.")
            return False
        except Exception as e:
            print(f"\n>> [SR-SERV] Erro: {e}")
            return False

    print(f"\n>> [SERVIDOR] Mensagem completa (SR) recebida: '{mensagem_completa}'")
    return True


def main():
    SHARED_KEY = b'Z7w1-8XNf7wJt7rXq4Y5zL3mP9nQ2vR6kS8tV5wX1yZ=' 
    seguranca = SecurityManager(SHARED_KEY)
    print(f">> [SEGURANÇA] Criptografia Ativada.")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('localhost', 1500))
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.listen(1)
        print(f"\n>> [SERVIDOR] Ouvindo em localhost 1500")

        sock_client, endereco = sock.accept()
        modo, tam_max = process_handshake(sock_client) 
        
        if modo and tam_max:
            comunicacao_cliente(sock_client, modo, seguranca)  

        sock_client.close()
    except Exception as e:
        print(f"Erro principal: {e}")
    finally:
        try:
            sock.close()
        except:
            pass

if __name__ == "__main__":
    main()