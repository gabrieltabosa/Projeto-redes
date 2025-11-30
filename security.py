from cryptography.fernet import Fernet

class SecurityManager:
    def __init__(self, key=None):
        if key:
            self.key = key
        else:
            self.key = Fernet.generate_key()
        
        self.cipher = Fernet(self.key)

    def get_key(self):
        return self.key

    def encrypt(self, message: str) -> str:
        if not message:
            return ""
        token_bytes = self.cipher.encrypt(message.encode('utf-8'))
        return token_bytes.decode('utf-8')

    def decrypt(self, token: str) -> str:

        if not token:
            return ""
        message_bytes = self.cipher.decrypt(token.encode('utf-8'))
        return message_bytes.decode('utf-8')