@@ -170,17 +170,29 @@ def enviar_janela(sock, pacotes, seq_inicial, tamanho_janela):
            ack_parts = data_ack.split(':')
            ack_num = int(ack_parts[1])

            # Se o ACK for o que esperamos (ACK cumulativo para o fim da janela)
            if data_ack.startswith("ACK") and ack_num >= seq_base + len(janela):
                # Sucesso, desliza a janela
                print(">> [CLIENTE] ACK cumulativo recebido. Janela enviada com sucesso.")
                num_pacote_enviado += len(janela) # Avança o número de pacotes enviados
                seq_base += len(janela) # Avança a base
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
                # NACK ou ACK fora da ordem
                print(f">> [CLIENTE] NACK recebido ou ACK inesperado (Esperado: >= {seq_base + len(janela)}, Recebido: {ack_num}) — retransmitindo janela atual...")
                # retransmite a mesma janela (não incrementa 'num_pacote_enviado' ou 'seq_base')
                # NACK real (e.g., NACK:46) ou ACK antigo (e.g., ACK:45)
                print(f">> [CLIENTE] NACK ou ACK antigo (Esperado: >= {expected_ack}, Recebido: {ack_num}) — retransmitindo janela atual...")
                continue
            # --- FIM DA CORREÇÃO ---

        except socket.timeout:
            print(f"\n>> [CLIENTE] TIMEOUT (esperando ACK para base {seq_base}) — retransmitindo janela atual...")
@@ -218,35 +230,32 @@ def main():

            seq = random.randint(0, 255) # Inicia o número de sequência

            while True:
                # 1. Configuração da Janela
                qnt_pacotes = int(input("\n>> [CLIENTE] Defina o tamanho da janela (pacotes por rajada): "))
                tamanho_caracteres = int(input(">> [CLIENTE] Defina o tamanho máximo de caracteres por pacote: "))
                
                if qnt_pacotes <= 0 or tamanho_caracteres <= 0:
                    print("Valores devem ser maiores que 0.")
                    continue

                # 2. Lendo e Segmentando a Mensagem
                message = input(f"\nDigite sua mensagem: ")
                pacotes = dividir_mensagem(tamanho_caracteres, message)
                print(f">> [CLIENTE] Mensagem dividida em {len(pacotes)} pacotes.")

                # 3. Informa ao servidor a configuração (Janela E Total)
                #    Isso é enviado DEPOIS de segmentar, para sabermos o total
                config_msg = f"{qnt_pacotes}|{len(pacotes)}"
                print(f">> [CLIENTE] Enviando configuração (Janela={qnt_pacotes}, Total={len(pacotes)})")
                sock.send(config_msg.encode('utf-8'))

                # 4. Envia a mensagem em janelas Go-Back-N
                seq = enviar_janela(sock, pacotes, seq, qnt_pacotes)

                # 5. Opção de sair
                sair = input("\nDigite 'sair' para encerrar a conexão ou pressione Enter para continuar...")
                if sair.lower() == 'sair':
                    print("Desconectando do servidor...")
                    sock.send("SAIR".encode('utf-8')) # Informa ao servidor
                    break
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
