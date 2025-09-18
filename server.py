import socket

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    sock.bind(('localhost', 1500))

    sock.listen(1)

    max_amount = 255

    print("waitng for three way handshake...")

    sock_client, client_adrres = sock.accept()

    syn = sock_client.recv(max_amount).decode()

    if syn:
        y = int(syn.split()[1])

        print(f"Server received: {syn}")

        seq = 5

        sock_client.sendall(str("ACK=" + str(y+1) + " SYN=" + str(seq)).encode('utf-8'))

        ack = sock_client.recv(max_amount).decode()
        
        if ack:
            print(f"Server received: {ack}")

    
if __name__ == "__main__":
    main()