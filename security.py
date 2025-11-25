from cryptography.fernet import Fernet

class SecurityManager:
    def __init__(self, key=None):
        """
        Inicializa o gerenciador de segurança.
        Se uma chave (bytes) for fornecida, ela é usada.
        Caso contrário, gera uma nova chave aleatória.
        """
        if key:
            self.key = key
        else:
            self.key = Fernet.generate_key()
        
        self.cipher = Fernet(self.key)

    def get_key(self):
        """Retorna a chave atual."""
        return self.key

    def encrypt(self, message: str) -> str:
        """
        Recebe uma string (texto plano).
        Retorna uma string criptografada (token Fernet em formato string).
        """
        if not message:
            return ""
        # Fernet opera com bytes. Convertemos str -> bytes, encriptamos, e voltamos bytes -> str
        token_bytes = self.cipher.encrypt(message.encode('utf-8'))
        return token_bytes.decode('utf-8')

    def decrypt(self, token: str) -> str:
        """
        Recebe uma string criptografada (token).
        Retorna a string original (texto plano).
        """
        if not token:
            return ""
        # Converte a string do token para bytes, descriptografa, e decodifica para string utf-8
        message_bytes = self.cipher.decrypt(token.encode('utf-8'))
        return message_bytes.decode('utf-8')