import socket
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
import base64


# noinspection PyInterpreter
class Network:
    def __init__(self):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # self.server = "10.11.250.207"
        self.server = "localhost"
        self.port = 5555
        self.server_public_key = None
        self.addr = (self.server, self.port)
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        self.public_key = self.private_key.public_key()
        self.connect()

    def connect(self):
        try:
            self.client.connect(self.addr)
            # Receive and set up public key
            public_key_str = self.receive()
            self.server_public_key = load_pem_public_key(
                public_key_str.encode(),
                backend=default_backend()
            )
        except:
            print("Unable to connect to server")

    def encrypt_message(self, message):
        encrypted_message = self.server_public_key.encrypt(
            message,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return base64.b64encode(encrypted_message)

    def send(self, data, receive=False):
        try:
            # Encrypt only the message, not the length prefix
            encrypted_message = data.encode()
            encrypted_length = len(encrypted_message)
            length_prefix = encrypted_length.to_bytes(4, byteorder='big')
            full_message = length_prefix + encrypted_message
            self.client.sendall(full_message)

            if receive:
                return self.receive()
            else:
                return None
        except socket.error as e:
            print(e)

    def receive(self):
        # First, receive the length of the message
        try:
            length_prefix = self.client.recv(4)
            if not length_prefix:
                return None
            message_length = int.from_bytes(length_prefix, byteorder='big')

            # Now receive the actual message
            full_message = b''
            while len(full_message) < message_length:
                packet = self.client.recv(message_length - len(full_message))
                if not packet:
                    return None
                full_message += packet
            return full_message.decode()
        except socket.error as e:
            print("Socket error: {}".format(e))
            return None
