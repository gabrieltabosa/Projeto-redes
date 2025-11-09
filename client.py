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

    # Escolhendo Erro a ser Simulado
    erro_simulado = None # Padrão: nenhum erro
    while True:
        selecao = input("\n>> [CLIENTE] Escolha se quer simular erros:\n(1) Sim\n(2) Não\nDigite sua escolha: ")
        if selecao == "1":
            erro_escolhido = input("\tSelecione o Erro a ser simulado\n\t(1) Timeout Erro\n\t(2) Pacote Duplicado\n\tdigite sua escolha: ")
            if erro_escolhido == "1":
                erro_simulado = "1"
                print("\tErro de TimeOut escolhido")
                break
            elif erro_escolhido == "2":
                erro_simulado = "2"
                print("\tErro de Duplicação de Pacotes escolhido")
                break
            else:
                print("\tOpção inválida! Tente novamente")
        elif selecao == "2":
            break
        else:
            print("Opção inválida! Tente Novamente")

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
        return modo, erro_simulado
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

            
        # Envia todos os pacotes da janela (pipelining)
        for i, msg in enumerate(janela):
            flag = "MSG"
            seq_atual = seq_base + i
        
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


def enviar_janela_sr(sock, pacotes, seq_inicial, tamanho_janela):
    
    seq_base = seq_inicial
    proximo_seq = seq_inicial
    total_pacotes_msg = len(pacotes)
    total_enviados = 0 # Conta pacotes confirmados (ACKados)
    
    pacotes_enviados_pendentes = {} 
    pacotes_ackados = set() 
    buffer_ack = "" # <--- NOVO BUFFER DE ACK

    print(f"\n>> [SR-CLIENTE] Iniciando envio SR. Base={seq_base}, Total={total_pacotes_msg}, Janela={tamanho_janela}")

    while total_enviados < total_pacotes_msg:
        
        # 1. Envia pacotes novos até o limite da janela
        while proximo_seq < (seq_base + tamanho_janela) and proximo_seq < (seq_inicial + total_pacotes_msg):
            
            idx = proximo_seq - seq_inicial
            msg = pacotes[idx]
            data_pacote = f"MSG|{msg}|{proximo_seq}"
            checksum = calculate_checksum(data_pacote)
            pacote_msg = f"{data_pacote}|{checksum}"

            pacotes_enviados_pendentes[proximo_seq] = pacote_msg 
            
            print(f">> [SR-CLIENTE] Enviando pacote {idx + 1}/{total_pacotes_msg} (SEQ={proximo_seq})")
            sock.send(pacote_msg.encode('utf-8'))
            time.sleep(0.01)
            
            proximo_seq += 1

        # 2. Espera por ACKs (com timeout focado na 'base')
        try:
            sock.settimeout(RETRANSMISSION_TIMEOUT)
            resposta = sock.recv(1024).decode('utf-8')
            buffer_ack += resposta # Adiciona dados recebidos ao buffer
            
            # Processa TODOS os pacotes completos no buffer (separados por \n)
            while '\n' in buffer_ack:
                pacote_ack_full, buffer_ack = buffer_ack.split('\n', 1)
                
                if not pacote_ack_full: # Ignora linhas vazias
                    continue

                is_valid, data_ack = verify_checksum(pacote_ack_full)
                if not is_valid:
                    print(f">> [SR-CLIENTE] Checksum do ACK inválido, descartando: {pacote_ack_full}")
                    continue

                # O Servidor SR envia ACKs individuais "ACK-SR:N"
                if data_ack.startswith("ACK-SR:"):
                    ack_num = int(data_ack.split(':')[1])
                    print(f">> [SR-CLIENTE] Recebido ACK-SR para {ack_num}")

                    # Se o ACK for para um pacote que ainda está pendente...
                    if ack_num in pacotes_enviados_pendentes:
                        pacotes_enviados_pendentes.pop(ack_num) # Remove dos pendentes
                        pacotes_ackados.add(ack_num)       # Adiciona aos ACKados
                        total_enviados += 1                # Incrementa o total
                        
                    # 3. Desliza a janela (a 'base')
                    # Se o ACK recebido for o da base, desliza a janela
                    # (Também desliza se a base já foi ACKada por um ACK fora de ordem)
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

        except socket.timeout:
            # 4. Timeout! Retransmite APENAS o pacote 'base'
            print(f"\n>> [SR-CLIENTE] TIMEOUT (esperando ACK para base {seq_base})")
            
            if seq_base in pacotes_enviados_pendentes:
                print(f">> [SR-CLIENTE] Retransmitindo pacote {seq_base}...")
                pacote_retransmitir = pacotes_enviados_pendentes[seq_base]
                sock.send(pacote_retransmitir.encode('utf-8'))
            else:
                # Se a base não está pendente, significa que o ACK dela foi recebido,
                # mas o loop 'while seq_base in pacotes_ackados' já a limpou.
                # O timeout foi, na verdade, para o *próximo* pacote (seq_base atual).
                if (seq_base - seq_inicial) < total_pacotes_msg:
                    print(f">> [SR-CLIENTE] Base {seq_base} não está pendente, mas timeout ocorreu.")
                    # Verifica se o próximo pacote (nova base) precisa ser enviado/reenviado
                    if seq_base in pacotes_enviados_pendentes:
                        print(f">> [SR-CLIENTE] Retransmitindo nova base {seq_base}...")
                        sock.send(pacotes_enviados_pendentes[seq_base].encode('utf-8'))
                else:
                    print(f">> [SR-CLIENTE] Timeout, mas todos os pacotes parecem enviados. Estranho.")


    print("\n>> [CLIENTE] Todos os pacotes da mensagem foram enviados com sucesso (SR)!")
    return seq_base # Retorna o novo número de sequência

def dividir_mensagem(tamanho_maximo, mensagem):
    partes = []
    if not mensagem: # Garante que envia pelo menos um pacote se a msg for vazia
        return [""]
    for i in range(0, len(mensagem), tamanho_maximo):
        partes.append(mensagem[i:i + tamanho_maximo])
    return partes


def main():
    try:
        # cria um objeto socket TCP e conecta ao servidor
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('localhost', 1500))

    except ConnectionRefusedError as error:
        print(f">> [CLIENTE] Aconteceu um erro ao tentar conectar ao servidor: {error}")
        print("Encerrando o programa...")
        return

    try:
        # Realiza o handshake com o servidor (modo e se há erro simulado)
        modo, erro_simulado = handshake(sock)

        seq = random.randint(0, 255)  # Inicia o número de sequência

        # Tamanho de caracteres fixo conforme solicitado
        tamanho_caracteres = 4
        print(f"\n>> [CLIENTE] Tamanho máximo de caracteres por pacote fixado em {tamanho_caracteres}.")

        # Se modo for GoBackN, solicita a janela; caso contrário usa 1 por padrão
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

                    break  # configuração válida
                except ValueError:
                    print("Por favor digite um número inteiro válido para a janela.")
        else:
            # Para Repetição Seletiva, usamos 1 como valor padrão.
            qnt_pacotes = 1
            print(f"\n>> [CLIENTE] Modo recebido: {modo}. Usando janela padrão = {qnt_pacotes} (não solicitada).")

        print("\n>> [CLIENTE] Configuração aceita. Agora você pode enviar várias mensagens.")
        print(">> Digite 'sair' para encerrar e desconectar.\n")

        # Loop principal de envio de mensagens
        while True:
            message = input("Digite sua mensagem (ou 'sair' para encerrar): ")
            if message.strip().lower() == "sair":
                print(">> [CLIENTE] Usuário solicitou encerrar. Saindo...")
                break

            # Segmenta a mensagem em pacotes usando o tamanho fixo
            pacotes = dividir_mensagem(tamanho_caracteres, message)
            print(f">> [CLIENTE] Mensagem dividida em {len(pacotes)} pacotes (tamanho por pacote = {tamanho_caracteres}).")

            # Informa ao servidor a configuração (Janela E Total) para essa mensagem
            config_msg = f"{qnt_pacotes}|{len(pacotes)}| {seq}"
            print(f">> [CLIENTE] Enviando configuração (Janela={qnt_pacotes}, Total={len(pacotes)})")
            try:
                sock.send(config_msg.encode('utf-8'))
            except Exception as e:
                print(f">> [CLIENTE] Erro ao enviar configuração: {e}")
                # continua permitindo novas tentativas
                continue

            # Chama a função de envio correta baseada no modo
            try:
                if modo == "GoBackN":
                    print_titulo("INICIANDO TRANSFERÊNCIA (MODO GO-BACK-N)")
                    seq = enviar_janela(sock, pacotes, seq, qnt_pacotes)
                elif modo == "RepetiçãoSeletiva":
                    print_titulo("INICIANDO TRANSFERÊNCIA (MODO REPETIÇÃO SELETIVA)")
                    # enviar_janela_sr pode ou não usar qnt_pacotes; adaptamos para aceitar
                    seq = enviar_janela_sr(sock, pacotes, seq, qnt_pacotes)
                else:
                    print(f">> [CLIENTE] Modo desconhecido recebido do handshake: {modo}")
                    continue

                print(f"\n>> [CLIENTE] Mensagem (Modo: {modo}) enviada com sucesso.\n")
            except Exception as e:
                print(f"\n>> [CLIENTE] Erro durante a transferência: {e}")
                # volta ao loop para permitir novas tentativas
                continue

    except Exception as e:
        print(f"\n>> [CLIENTE] Erro na comunicação: {e}")

    finally:
        # Fecha a conexão
        try:
            sock.close()
        except Exception:
            pass
        print(">> [CLIENTE] Conexão fechada.")



if __name__ == "__main__":
    main()
