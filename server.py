import numpy as np
import socket
from _thread import *
import pickle
from snake import SnakeGame
import uuid
import time

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

    def broadcast_message(self, sender_id, message):
        for player_id in self.game.players:
            if player_id != sender_id:
                try:
                    player_conn = self.player_connections[player_id]
                    player_conn.send("{}: {}".format(sender_id, player_id).encode())
                except Exception as e:
                    print("Error broadcasting message to player {}: {}".format(player_id, e))

    def client_thread(self, conn, unique_id):
        self.player_connections[unique_id] = conn
        while True:
            try:
                data = conn.recv(BUFFER_SIZE).decode()
                conn.send(self.game_state.encode())
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
                elif data != "control:get":
                    print("Invalid data received from client:", data)
                if data.startswith("chat:"):
                    message = data.split(":", 1)[1]
                    self.broadcast_message(unique_id, message)
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
