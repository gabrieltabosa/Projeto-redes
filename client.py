import socket

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('localhost', 1500))

    max_amount = 255

    seq = 1

    sock.sendall(str("SYN " + str(seq)).encode('utf-8'))

    syn_ack = sock.recv(max_amount).decode()


    if syn_ack:
        ack_part = int(syn_ack.split()[1].split("=")[1]) + 1

        print(f"Client received: {syn_ack}")

        sock.sendall(str("ACK="+ str(ack_part)).encode('utf-8'))

if __name__ == "__main__":
    main()