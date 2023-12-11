import numpy as np
import socket
from _thread import *
import pickle
from snake import SnakeGame
import uuid
import time
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
import base64

SERVER = "localhost"
PORT = 5555
ROWS = 20
BUFFER_SIZE = 2048
INTERVAL = 0.2

RGB_COLORS = {
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
    "orange": (255, 165, 0),
}
RGB_COLORS_LIST = list(RGB_COLORS.values())


class GameServer:
    def __init__(self, host, port):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.server_socket.bind((host, port))
        except socket.error as e:
            print(str(e))
        self.server_socket.listen(2)
        self.game = SnakeGame(ROWS)
        self.game_state = ""
        self.moves_queue = set()
        self.player_connections = {}
        # RSA Key Generation
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        self.public_key = self.private_key.public_key()
        print("Waiting for a connection, Server Started")

    def run(self):
        start_new_thread(self.game_thread, ())
        while True:
            conn, addr = self.server_socket.accept()
            print("Connected to:", addr)
            unique_id = str(uuid.uuid4())
            color = RGB_COLORS_LIST[np.random.randint(0, len(RGB_COLORS_LIST))]
            self.game.add_player(unique_id, color=color)
            start_new_thread(self.client_thread, (conn, unique_id))

    def send(self, conn, message):
        # Encode the message and prepend length
        encoded_message = message.encode()
        message_length = len(encoded_message)
        length_prefix = message_length.to_bytes(4, byteorder='big')
        full_message = length_prefix + encoded_message
        conn.sendall(full_message)

    def decrypt_message(self, encrypted_message):
        decrypted_message = self.private_key.decrypt(
            base64.b64decode(encrypted_message),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return decrypted_message.decode()

    def serialize_public_key(self):
        public_key = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return public_key.decode('utf-8')

    def receive(self, conn):
        try:
            # Receive the length of the encrypted message
            encrypted_length_prefix = conn.recv(4)
            if not encrypted_length_prefix:
                return None
            encrypted_message_length = int.from_bytes(encrypted_length_prefix, byteorder='big')

            # Now receive the actual encrypted message
            encrypted_message = b''
            while len(encrypted_message) < encrypted_message_length:
                packet = conn.recv(encrypted_message_length - len(encrypted_message))
                if not packet:
                    return None
                encrypted_message += packet

            # Decrypt the message after receiving the full encrypted message
            return self.decrypt_message(encrypted_message)
        except Exception as e:
            print("Error receiving data: {}".format(e))
            return None

    def broadcast_message(self, sender_id, message):
        for player_id in self.game.players:
            if player_id != sender_id:
                try:
                    player_conn = self.player_connections[player_id]
                    self.send(player_conn, "chat:{}: {}".format(sender_id, message))
                except Exception as e:
                    print("Error broadcasting message to player {}: {}".format(player_id, e))

    def client_thread(self, conn, unique_id):
        self.player_connections[unique_id] = conn
        public_key_str = self.serialize_public_key()
        self.send(conn, public_key_str) # Send public key to client
        while True:
            try:
                data = self.receive(conn)
                self.send(conn, "pos:{}".format(self.game_state))
                if not data:
                    print("no data received from client")
                    break
                elif data == "quit":
                    print("received quit")
                    self.game.remove_player(unique_id)
                    break
                elif data == "reset":
                    self.game.reset_player(unique_id)
                elif data in ["up", "down", "left", "right"]:
                    move = data
                    self.moves_queue.add((unique_id, move))
                elif data.startswith("chat:"):
                    message = data.split(":", 1)[1]
                    self.broadcast_message(unique_id, message)
                elif data != "control:get":
                    print("Invalid data received from client:", data)
            except:
                print("Player {} disconnected".format(unique_id))
                break
        print("Connection with Player {} closed".format(unique_id))
        self.game.remove_player(unique_id)
        del self.player_connections[unique_id]
        conn.close()

    def game_thread(self):
        while True:
            last_move_timestamp = time.time()
            self.game.move(self.moves_queue)
            self.moves_queue = set()
            self.game_state = self.game.get_state()
            while time.time() - last_move_timestamp < INTERVAL:
                time.sleep(0.1)


def main():
    server = GameServer(SERVER, PORT)
    server.run()


if __name__ == "__main__":
    main()
