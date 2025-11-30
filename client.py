import random
import socket
import time
from security import SecurityManager

# tempo do timeout de retransmissão
RETRANSMISSION_TIMEOUT = 3.0 

# funções auxiliares

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

# lógica do protocolo

def handshake(sock):
    print_titulo("INICIANDO HANDSHAKE COM O SERVIDOR")

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

    erro_simulado = None 
    while True:
        selecao = input("\n>> [CLIENTE] Escolha se quer simular erros:\n(1) Sim\n(2) Não\nDigite sua escolha: ")
        if selecao == "1":
            erro_escolhido = input("\tSelecione o Erro a ser simulado\n\t(1) Timeout Erro\n\t(2) Pacote Duplicado\n\t(3) Perda de Pacotes (Garantida)\n\t(4) Pacote Corrompido\n\tdigite sua escolha: ")
            if erro_escolhido == "1":
                erro_simulado = "1"
                print("\tErro de TimeOut escolhido")
                break
            elif erro_escolhido == "2":
                erro_simulado = "2"
                print("\tErro de Duplicação de Pacotes escolhido")
                break
            elif erro_escolhido == "3":
                erro_simulado = "3"
                print("\tErro de Perda de Pacotes (GARANTIDA) escolhido")
                break
            elif erro_escolhido == "4":
                erro_simulado = "4"
                print("\tErro de Pacote Corrompido escolhido")
                break
            else:
                print("\tOpção inválida! Tente novamente")
        elif selecao == "2":
            break
        else:
            print("Opção inválida! Tente Novamente")

    tam_max = "1024"
    print(f"\n>> [CLIENTE] Tamanho pré-definido de mensagem: {tam_max}")
    
    data_syn = f"SYN|{modo}|{tam_max}"
    checksum_syn = calculate_checksum(data_syn)
    mensagem = f"{data_syn}|{checksum_syn}"
    
    print(f"\n>> [CLIENTE] Enviando SYN para o servidor: {mensagem}")
    sock.send(mensagem.encode('utf-8'))

    print("\n>> [CLIENTE] Aguardando resposta SYN-ACK do servidor...")
    resposta = sock.recv(1024).decode('utf-8')
    print(f">> [CLIENTE] Resposta recebida: {resposta}")

    is_valid, data_syn_ack = verify_checksum(resposta)
    if not is_valid:
        print_titulo("ERRO NO HANDSHAKE - Checksum do SYN-ACK inválido")
        raise Exception("Falha no Handshake: Checksum inválido")

    partes = data_syn_ack.split("|")
    if data_syn_ack.startswith("SYN-ACK") and partes[1] == modo and partes[2] == tam_max:
        print("\n>> [CLIENTE] Enviando ACK para o servidor...")
        
        data_ack = "ACK"
        checksum_ack = calculate_checksum(data_ack)
        mensagem_ack = f"{data_ack}|{checksum_ack}"
        
        sock.send(mensagem_ack.encode('utf-8'))
        print_titulo("HANDSHAKE COM O SERVIDOR ESTABELECIDO")
        return modo, erro_simulado
    else:
        print_titulo("ERRO NO HANDSHAKE")
        raise Exception("Falha no Handshake")


def enviar_janela(sock, pacotes, seq_inicial, tamanho_janela, erro_simulado, seguranca):

    # função do modo GBN
    
    seq_base = seq_inicial 
    total_pacotes = len(pacotes)
    num_pacote_enviado = 0 

    # variáveis para fast retransmit
    acks_duplicados = 0
    pode_enviar = True 

    # lógica pra sortear a perda
    pacote_azarado = -1
    if erro_simulado == "3" and total_pacotes > 0:
        pacote_azarado = random.randint(0, total_pacotes - 1)
        print(f">> [DEBUG-SISTEMA] O pacote de índice {pacote_azarado + 1} (1-based) foi sorteado para ser PERDIDO.")

    while num_pacote_enviado < total_pacotes:
        idx_inicio = num_pacote_enviado
        idx_fim = min(num_pacote_enviado + tamanho_janela, total_pacotes)
        janela = pacotes[idx_inicio:idx_fim]
        
        if pode_enviar:
            print(f"\n>> [CLIENTE] Enviando janela (Pacotes {idx_inicio+1} a {idx_fim} de {total_pacotes})... (Base: {seq_base})")

            # loop de envio da janela
            for i, msg in enumerate(janela):
                flag = "MSG"
                seq_atual = seq_base + i
                indice_absoluto = idx_inicio + i 
                
                msg_encriptada = seguranca.encrypt(msg)
                
                data_pacote = f"{flag}|{msg_encriptada}|{seq_atual}"
                checksum = calculate_checksum(data_pacote)
                pacote_msg = f"{data_pacote}|{checksum}"
                
                # lógica perda garantida
                if erro_simulado == "3":
                    if indice_absoluto == pacote_azarado:
                        print(f">> [CLIENTE-ERRO] SIMULANDO PERDA GARANTIDA do pacote {indice_absoluto + 1}/{total_pacotes} (SEQ={seq_atual})...")
                        pacote_azarado = -1 
                        time.sleep(0.01)
                        continue 

                # lógica do modo corrompido
                elif erro_simulado == "4" and random.random() < 0.10: 
                    dados_corrompidos = data_pacote + "X" 
                    pacote_corrompido = f"{dados_corrompidos}|{checksum}"
                    print(f">> [CLIENTE-ERRO] SIMULANDO CORRUPÇÃO do pacote {indice_absoluto + 1}/{total_pacotes} (SEQ={seq_atual}).")
                    sock.send((pacote_corrompido + "\n").encode('utf-8'))
                    time.sleep(0.01)
                    continue 

                # envio normal
                print(f">> [CLIENTE] Enviando pacote {indice_absoluto + 1}/{total_pacotes} (SEQ={seq_atual}) [Criptografado]")
                sock.send((pacote_msg + "\n").encode('utf-8'))
                time.sleep(0.01) 
            
            pode_enviar = False

        # espera por resposta
        try:
            print(">> [CLIENTE] Aguardando confirmação (ACK)...")
            sock.settimeout(RETRANSMISSION_TIMEOUT)
            resposta = sock.recv(1024).decode('utf-8')
            print(f">> [CLIENTE] Resposta do servidor: {resposta}")

            is_valid, data_ack = verify_checksum(resposta)
            if not is_valid:
                print(">> [CLIENTE] Checksum do ACK inválido — Ignorando...")
                continue 
                
            ack_parts = data_ack.split(':')
            ack_num = int(ack_parts[1])
            
            expected_ack = seq_base + len(janela)

            if ack_num >= expected_ack:
                # ACK novo e válido
                if data_ack.startswith("ACK"):
                    print(">> [CLIENTE] ACK cumulativo recebido. Janela confirmada.")
                else: 
                    print(f">> [CLIENTE] NACK recebido ({ack_num}) >= Esperado. Avançando...")
                
                num_pacote_enviado += len(janela) 
                seq_base += len(janela)
                
                acks_duplicados = 0
                pode_enviar = True
            
            else:
                # falha, ACK antigo ou NACK
                acks_duplicados += 1
                print(f">> [CLIENTE] ACK Duplicado/Antigo #{acks_duplicados} recebido (Base: {ack_num}).")

                if acks_duplicados == 3:
                    print(">> [CLIENTE] 3 ACKs Duplicados recebidos -> FAST RETRANSMIT!")
                    acks_duplicados = 0
                    pode_enviar = True 
                else:
                    pode_enviar = False 
                    continue

        except (socket.timeout, TimeoutError):
            print(f">> [CLIENTE] TIMEOUT ({RETRANSMISSION_TIMEOUT}s) — Estourou o tempo limite.")
            print(">> [CLIENTE] Retransmitindo janela por Timeout...")
            acks_duplicados = 0 
            pode_enviar = True # forçar o reenvio
            continue 

    print("\n>> [CLIENTE] Todos os pacotes da mensagem foram enviados com sucesso!")
    return seq_base


def enviar_janela_sr(sock, pacotes, seq_inicial, tamanho_janela, erro_simulado, seguranca):
    """
    Função do SR
    """
    seq_base = seq_inicial
    proximo_seq = seq_inicial
    total_pacotes_msg = len(pacotes)
    total_enviados = 0 
    
    pacotes_enviados_pendentes = {} 
    pacotes_ackados = set() 
    buffer_ack = "" 

    pacote_azarado = -1
    if erro_simulado == "3" and total_pacotes_msg > 0:
        pacote_azarado = random.randint(0, total_pacotes_msg - 1)
        print(f">> [DEBUG-SISTEMA-SR] O pacote de índice {pacote_azarado + 1} foi sorteado para ser PERDIDO.")

    print(f"\n>> [SR-CLIENTE] Iniciando envio SR. Base={seq_base}, Total={total_pacotes_msg}, Janela={tamanho_janela}")

    while total_enviados < total_pacotes_msg:
        
        while proximo_seq < (seq_base + tamanho_janela) and proximo_seq < (seq_inicial + total_pacotes_msg):
            
            idx = proximo_seq - seq_inicial
            msg = pacotes[idx]
            
            msg_encriptada = seguranca.encrypt(msg)

            data_pacote = f"MSG|{msg_encriptada}|{proximo_seq}"
            checksum = calculate_checksum(data_pacote)
            pacote_msg = f"{data_pacote}|{checksum}"

            pacotes_enviados_pendentes[proximo_seq] = pacote_msg 
            
            if erro_simulado == "3":
                if idx == pacote_azarado:
                    print(f">> [SR-CLIENTE-ERRO] SIMULANDO PERDA GARANTIDA do pacote {idx + 1}/{total_pacotes_msg} (SEQ={proximo_seq})...")
                    pacote_azarado = -1 
                    time.sleep(0.01)
                    proximo_seq += 1 
                    continue
            
            elif erro_simulado == "4" and random.random() < 0.10: 
                dados_corrompidos = data_pacote + "X" 
                pacote_corrompido = f"{dados_corrompidos}|{checksum}"
                print(f">> [SR-CLIENTE-ERRO] SIMULANDO CORRUPÇÃO do pacote {idx + 1}/{total_pacotes_msg} (SEQ={proximo_seq}).")
                sock.send((pacote_corrompido + "\n").encode('utf-8'))
                time.sleep(0.01)
                proximo_seq += 1 
                continue 
                
            print(f">> [SR-CLIENTE] Enviando pacote {idx + 1}/{total_pacotes_msg} (SEQ={proximo_seq}) [Criptografado]")
            # ADICIONADO O \n
            sock.send((pacote_msg + "\n").encode('utf-8'))
            time.sleep(0.01)
            
            proximo_seq += 1

        try:
            sock.settimeout(RETRANSMISSION_TIMEOUT)
            resposta = sock.recv(1024).decode('utf-8')
            buffer_ack += resposta 
            
            while '\n' in buffer_ack:
                pacote_ack_full, buffer_ack = buffer_ack.split('\n', 1)
                
                if not pacote_ack_full: 
                    continue

                is_valid, data_ack = verify_checksum(pacote_ack_full)
                if not is_valid:
                    print(f">> [SR-CLIENTE] Checksum do ACK inválido, descartando: {pacote_ack_full}")
                    continue

                if data_ack.startswith("ACK-SR:"):
                    ack_num = int(data_ack.split(':')[1])
                    print(f">> [SR-CLIENTE] Recebido ACK-SR para {ack_num}")

                    if ack_num in pacotes_enviados_pendentes:
                        pacotes_enviados_pendentes.pop(ack_num) 
                        pacotes_ackados.add(ack_num)      
                        total_enviados += 1               
                        
                    while seq_base in pacotes_ackados:
                        if seq_base == ack_num:
                            print(f">> [SR-CLIENTE] ACK da base ({seq_base}) recebido.")
                        else:
                            print(f">> [SR-CLIENTE] Base ({seq_base}) já estava ACKada. Deslizando...")
                        
                        pacotes_ackados.remove(seq_base)
                        seq_base += 1
                    
                    print(f">> [SR-CLIENTE] Janela deslizou. Nova base: {seq_base}")
                    
                else:
                    print(f">> [SR-CLIENTE] Resposta inesperada do servidor: {data_ack}")

        except (socket.timeout, TimeoutError):
            print(f">> [SR-CLIENTE] TIMEOUT ({RETRANSMISSION_TIMEOUT}s) - Esperando ACK base {seq_base}")
            
            if seq_base in pacotes_enviados_pendentes:
                print(f">> [SR-CLIENTE] Retransmitindo pacote {seq_base} (Base) para forçar o ACK...")
                pacote_retransmitir = pacotes_enviados_pendentes[seq_base]
                sock.send((pacote_retransmitir + "\n").encode('utf-8'))
            else:
                if pacotes_enviados_pendentes:
                    seq_a_retransmitir = min(pacotes_enviados_pendentes.keys())
                    print(f">> [SR-CLIENTE] Retransmitindo pacote {seq_a_retransmitir} (Menor pendente)...")
                    pacote_retransmitir = pacotes_enviados_pendentes[seq_a_retransmitir]
                    sock.send((pacote_retransmitir + "\n").encode('utf-8'))

    print("\n>> [CLIENTE] Todos os pacotes da mensagem foram enviados com sucesso (SR)!")
    return seq_base 

def dividir_mensagem(tamanho_maximo, mensagem):
    partes = []
    if not mensagem: 
        return [""]
    for i in range(0, len(mensagem), tamanho_maximo):
        partes.append(mensagem[i:i + tamanho_maximo])
    return partes


def main():

    # criptografia
    SHARED_KEY = b'Z7w1-8XNf7wJt7rXq4Y5zL3mP9nQ2vR6kS8tV5wX1yZ=' 
    seguranca = SecurityManager(SHARED_KEY)
    print(f">> [SEGURANÇA] Criptografia Ativada.")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('localhost', 1500))

    except ConnectionRefusedError as error:
        print(f">> [CLIENTE] Aconteceu um erro ao tentar conectar ao servidor: {error}")
        print("Encerrando o programa...")
        return

    try:
        modo, erro_simulado = handshake(sock)

        seq = random.randint(0, 255)  
        tamanho_caracteres = 4
        print(f"\n>> [CLIENTE] Tamanho máximo de caracteres por pacote fixado em {tamanho_caracteres}.")

        if modo == "GoBackN":
            while True:
                try:
                    qnt_pacotes = int(input("\n>> [CLIENTE] Defina o tamanho da janela (pacotes por rajada): "))

                    if qnt_pacotes <= 0:
                        print("Valores devem ser maiores que 0.")
                        continue
                    if qnt_pacotes > 5:
                        print("Valor da janela deve ser menor ou igual a 5.")
                        continue

                    break  
                except ValueError:
                    print("Por favor digite um número inteiro válido para a janela.")
        else:
            qnt_pacotes = 4 
            print(f"\n>> [CLIENTE] Modo recebido: {modo}. Usando janela padrão = {qnt_pacotes} para SR.")

        print("\n>> [CLIENTE] Configuração aceita. Agora você pode enviar várias mensagens.")
        print(">> Digite 'sair' para encerrar e desconectar.\n")

        while True:
            message = input("Digite sua mensagem (ou 'sair' para encerrar): ")
            if message.strip().lower() == "sair":
                print(">> [CLIENTE] Usuário solicitou encerrar. Saindo...")
                break

            pacotes = dividir_mensagem(tamanho_caracteres, message)
            print(f">> [CLIENTE] Mensagem dividida em {len(pacotes)} pacotes.")

            config_data = f"{qnt_pacotes}|{len(pacotes)}|{seq}"
            checksum_config = calculate_checksum(config_data)
            config_msg_full = f"{config_data}|{checksum_config}"
            
            print(f">> [CLIENTE] Enviando configuração (Janela={qnt_pacotes}, Total={len(pacotes)}, Base={seq})")
            try:
                sock.send(config_msg_full.encode('utf-8'))

                time.sleep(0.2) 
            except Exception as e:
                print(f">> [CLIENTE] Erro ao enviar configuração: {e}")
                continue

            try:
                if modo == "GoBackN":
                    print_titulo("INICIANDO TRANSFERÊNCIA (MODO GO-BACK-N)")
                    seq = enviar_janela(sock, pacotes, seq, qnt_pacotes, erro_simulado, seguranca)
                elif modo == "RepetiçãoSeletiva":
                    print_titulo("INICIANDO TRANSFERÊNCIA (MODO REPETIÇÃO SELETIVA)")
                    seq = enviar_janela_sr(sock, pacotes, seq, qnt_pacotes, erro_simulado, seguranca)
                else:
                    print(f">> [CLIENTE] Modo desconhecido recebido do handshake: {modo}")
                    continue

                print(f"\n>> [CLIENTE] Mensagem (Modo: {modo}) enviada com sucesso.\n")
            except Exception as e:
                print(f"\n>> [CLIENTE] Erro durante a transferência: {e}")
                continue

    except Exception as e:
        print(f"\n>> [CLIENTE] Erro na comunicação: {e}")

    finally:
        try:
            sock.send("SAIR".encode('utf-8'))
        except Exception:
            pass 
        try:
            sock.close()
        except Exception:
            pass
        print(">> [CLIENTE] Conexão fechada.")


if __name__ == "__main__":
    main()