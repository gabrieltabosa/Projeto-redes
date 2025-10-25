import random
import socket
import time

RETRANSMISSION_TIMEOUT = 5.0 # Aumentei o timeout para dar tempo da janela ser processada

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
    
    # Adiciona checksum
    data_syn = f"SYN|{modo}|{tam_max}"
    checksum_syn = calculate_checksum(data_syn)
    mensagem = f"{data_syn}|{checksum_syn}"
    
    print(f"\n>> [CLIENTE] Enviando SYN para o servidor: {mensagem}")
    sock.send(mensagem.encode('utf-8'))

    # 2. Recebendo o SYN-ACK do Servidor
    print("\n>> [CLIENTE] Aguardando resposta SYN-ACK do servidor...")
    resposta = sock.recv(1024).decode('utf-8')
    print(f">> [CLIENTE] Resposta recebida: {resposta}")

    # Verifica o checksum
    is_valid, data_syn_ack = verify_checksum(resposta)
    if not is_valid:
        print_titulo("ERRO NO HANDSHAKE - Checksum do SYN-ACK inválido")
        raise Exception("Falha no Handshake: Checksum inválido")

    # Conferindo resposta (usando data_syn_ack verificado)
    partes = data_syn_ack.split("|")
    if data_syn_ack.startswith("SYN-ACK") and partes[1] == modo and partes[2] == tam_max:
        # 3. Enviando ACK ao servidor
        print("\n>> [CLIENTE] Enviando ACK para o servidor...")
        
        # Adiciona checksum
        data_ack = "ACK"
        checksum_ack = calculate_checksum(data_ack)
        mensagem_ack = f"{data_ack}|{checksum_ack}"
        
        sock.send(mensagem_ack.encode('utf-8'))
        print_titulo("HANDSHAKE COM O SERVIDOR ESTABELECIDO")
    else:
        print_titulo("ERRO NO HANDSHAKE")
        raise Exception("Falha no Handshake")


def enviar_janela(sock, pacotes, seq_inicial, tamanho_janela):
    seq_base = seq_inicial # O início da janela (o ACK que esperamos)
    total_pacotes = len(pacotes)
    num_pacote_enviado = 0 # O índice do pacote na lista `pacotes`

    while num_pacote_enviado < total_pacotes:
        # Cria a janela atual
        idx_inicio = num_pacote_enviado
        idx_fim = min(num_pacote_enviado + tamanho_janela, total_pacotes)
        janela = pacotes[idx_inicio:idx_fim]
        
        print(f"\n>> [CLIENTE] Enviando janela (Pacotes {idx_inicio+1} a {idx_fim} de {total_pacotes})... (Base: {seq_base})")

        # --- LÓGICA DE SIMULAÇÃO DE FALHA ---
        tipo_falha = "NENHUMA"
        if random.randint(1, 3) == 1: # 33% de chance de falha na janela
            tipo_falha = random.choice(["PERDA", "CORRUPCAO"])
            
        pacote_com_falha = -1
        if tipo_falha != "NENHUMA":
            pacote_com_falha = random.randint(0, len(janela) - 1)
            print(f">> [CLIENTE] (SIMULANDO FALHA: {tipo_falha} no pacote {idx_inicio + pacote_com_falha + 1})")
        # --- FIM DA SIMULAÇÃO ---
            
        # Envia todos os pacotes da janela (pipelining)
        for i, msg in enumerate(janela):
            flag = "MSG"
            seq_atual = seq_base + i
            
            # Aplica a falha, se houver
            if i == pacote_com_falha:
                if tipo_falha == "PERDA":
                    print(f">> [CLIENTE] (Pulando envio do pacote {idx_inicio + i + 1}...)")
                    continue # Simplesmente não envia o pacote
                elif tipo_falha == "CORRUPCAO":
                    # Enviamos com flag "PERDA" para simular corrupção
                    flag = "PERDA" 

            data_pacote = f"{flag}|{msg}|{seq_atual}"
            checksum = calculate_checksum(data_pacote)
            pacote_msg = f"{data_pacote}|{checksum}"
            
            print(f">> [CLIENTE] Enviando pacote {idx_inicio + i + 1}/{total_pacotes} (SEQ={seq_atual})")
            sock.send(pacote_msg.encode('utf-8'))
            time.sleep(0.01) # Pequeno delay para não sobrecarregar o buffer do servidor

        # Espera resposta do servidor após enviar toda a janela
        try:
            sock.settimeout(RETRANSMISSION_TIMEOUT)
            resposta = sock.recv(1024).decode('utf-8')
            print(f"\n>> [CLIENTE] Resposta do servidor: {resposta}")

            # Verifica o checksum da resposta
            is_valid, data_ack = verify_checksum(resposta)
            if not is_valid:
                print(">> [CLIENTE] Checksum do ACK/NACK inválido — retransmitindo janela atual...")
                continue
                
            ack_parts = data_ack.split(':')
            ack_num = int(ack_parts[1])
            
            # --- INÍCIO DA CORREÇÃO ---
            # O ACK que esperamos para *esta* janela
            expected_ack = seq_base + len(janela)

            # Se o ACK/NACK do servidor for >= ao que esperamos,
            # significa que ele recebeu esta janela (ou já está à frente).
            # Isso corrige o bug do ACK perdido (Livelock).
            if ack_num >= expected_ack:
                if data_ack.startswith("ACK"):
                    print(">> [CLIENTE] ACK cumulativo recebido. Janela enviada com sucesso.")
                else: # Ex: NACK:48 recebido quando esperávamos 48
                    print(f">> [CLIENTE] NACK recebido ({ack_num}), mas é >= ao esperado ({expected_ack}).")
                    print(">> [CLIENTE] Tratando como ACK implícito (ACK da janela anterior foi perdido). Avançando janela...")
                
                # Desliza a janela em ambos os casos
                num_pacote_enviado += len(janela) 
                seq_base += len(janela) 
            
            else:
                # NACK real (e.g., NACK:46) ou ACK antigo (e.g., ACK:45)
                print(f">> [CLIENTE] NACK ou ACK antigo (Esperado: >= {expected_ack}, Recebido: {ack_num}) — retransmitindo janela atual...")
                continue
            # --- FIM DA CORREÇÃO ---

        except socket.timeout:
            print(f"\n>> [CLIENTE] TIMEOUT (esperando ACK para base {seq_base}) — retransmitindo janela atual...")
            # retransmite a mesma janela (não incrementa)
            continue

    print("\n>> [CLIENTE] Todos os pacotes da mensagem foram enviados com sucesso!")
    return seq_base # Retorna o novo número de sequência para a próxima mensagem


def dividir_mensagem(tamanho_maximo, mensagem):
    partes = []
    if not mensagem: # Garante que envia pelo menos um pacote se a msg for vazia
        return [""]
    for i in range(0, len(mensagem), tamanho_maximo):
        partes.append(mensagem[i:i + tamanho_maximo])
    return partes


def main():

    try:
        # cria um objeto socket TCP
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('localhost', 1500))
        
    except ConnectionRefusedError as error:
        print(f">> [CLIENTE] Aconteceu um erro ao tentar conectar ao servidor: {error}")
        print("Encerrando o programa...")
        
    else:
        try:
            # Realiza o handshake com o servidor
            handshake(sock)

            seq = random.randint(0, 255) # Inicia o número de sequência

            # O cliente agora executa apenas UMA vez e sai
            
            # 1. Configuração da Janela
            qnt_pacotes = int(input("\n>> [CLIENTE] Defina o tamanho da janela (pacotes por rajada): "))
            tamanho_caracteres = int(input(">> [CLIENTE] Defina o tamanho máximo de caracteres por pacote: "))
            
            if qnt_pacotes <= 0 or tamanho_caracteres <= 0:
                print("Valores devem ser maiores que 0.")
                raise Exception("Valores de janela ou pacote inválidos.")

            # 2. Lendo e Segmentando a Mensagem
            message = input(f"\nDigite sua mensagem: ")
            pacotes = dividir_mensagem(tamanho_caracteres, message)
            print(f">> [CLIENTE] Mensagem dividida em {len(pacotes)} pacotes.")

            # 3. Informa ao servidor a configuração (Janela E Total)
            config_msg = f"{qnt_pacotes}|{len(pacotes)}"
            print(f">> [CLIENTE] Enviando configuração (Janela={qnt_pacotes}, Total={len(pacotes)})")
            sock.send(config_msg.encode('utf-8'))

            # 4. Envia a mensagem em janelas Go-Back-N
            seq = enviar_janela(sock, pacotes, seq, qnt_pacotes)

            # 5. Encerra automaticamente
            print("\n>> [CLIENTE] Mensagem enviada com sucesso. Desconectando...")
            sock.send("SAIR".encode('utf-8')) # Informa ao servidor que terminamos
                    
        except Exception as e:
            print(f"\n>> [CLIENTE] Erro na comunicação: {e}")
            
        finally:
            # Fecha a conexão
            sock.close()
            print(">> [CLIENTE] Conexão fechada.")

if __name__ == "__main__":
    main()