import numpy as np
import pygame
from network import Network
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import load_pem_public_key
import base64

WIDTH = 500
HEIGHT = 500
ROWS = 20
RGB_COLORS = {
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
    "orange": (255, 165, 0),
}
RGB_COLOR_LIST = list(RGB_COLORS.values())
PREDEFINED_MESSAGES = {
    pygame.K_z: "Congratulations!",
    pygame.K_x: "It works!",
    pygame.K_c: "Ready?"
}
KEYS = {
    pygame.K_LEFT: "left",
    pygame.K_RIGHT: "right",
    pygame.K_UP: "up",
    pygame.K_DOWN: "down",
    pygame.K_SPACE: "reset",
}

def draw_grid(w, surface):
    global ROWS
    sizeBtwn = w // ROWS
    x = 0
    y = 0
    for l in range(ROWS):
        x = x + sizeBtwn
        y = y + sizeBtwn
        pygame.draw.line(surface, (255, 255, 255), (x, 0), (x, w))
        pygame.draw.line(surface, (255, 255, 255), (0, y), (w, y))


def draw_things(surface, positions, color=None, eye=False):
    global WIDTH, RGB_COLOR_LIST
    dis = WIDTH // ROWS
    if color is None:
        color = (np.random.randint(0, 255), np.random.randint(0, 255), np.random.randint(0, 255))
    for pos_id, pos in enumerate(positions):
        i, j = pos
        pygame.draw.rect(surface, color, (i * dis + 1, j * dis + 1, dis - 2, dis - 2))
        if eye and pos_id == 0:
            centre = dis // 2
            radius = 3
            circleMiddle = (i * dis + centre - radius, j * dis + 8)
            circleMiddle2 = (i * dis + dis - radius * 2, j * dis + 8)
            pygame.draw.circle(surface, (0, 0, 0), circleMiddle, radius)
            pygame.draw.circle(surface, (0, 0, 0), circleMiddle2, radius)


def draw(surface, players, snacks):
    global RGB_COLOR_LIST
    surface.fill((0, 0, 0))
    draw_grid(WIDTH, surface)
    for i, player in enumerate(players):
        color = RGB_COLOR_LIST[i % len(RGB_COLOR_LIST)]
        draw_things(surface, player, color=color, eye=True)
    draw_things(surface, snacks, (0, 255, 0))
    pygame.display.flip()


class GameClient:
    def __init__(self):
        pygame.init()
        self.win = pygame.display.set_mode((WIDTH, HEIGHT), pygame.DOUBLEBUF)
        self.network = Network()
        self.shouldRun = True
        self.run()

    def run(self):
        while self.shouldRun:
            events = pygame.event.get()
            server_response = self.handle_events(events)
            pos = self.handle_server_response(server_response)
            if pos:
                snacks, players = self.parse_pos(pos)
                draw(self.win, players, snacks)
        pygame.quit()

    def handle_server_response(self, server_response):
        if server_response is None:
            return None
        pos_data = None
        if "chat:" in server_response:
            parts = server_response.split("chat:")
            chat_message = parts[1].split("pos:")[0] if "pos:" in parts[1] else parts[1]
            print(chat_message)
        if "pos:" in server_response:
            parts = server_response.split("pos:")
            pos_data = parts[1].split("chat:")[0] if "chat:" in parts[1] else parts[1]
        return pos_data.strip() if pos_data else None

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.QUIT:
                self.shouldRun = False
                return self.network.send("quit", receive=True)
            if event.type == pygame.KEYDOWN:
                return self.get_key_input(event)
        return self.network.send("control:get", receive=True)

    def get_key_input(self, event):
        if event.key in KEYS:
            return self.network.send(KEYS[event.key], receive=True)
        elif event.key in PREDEFINED_MESSAGES:
            return self.network.send("chat:{}".format(PREDEFINED_MESSAGES[event.key]), receive=True)
        return None

    def parse_pos(self, pos):
        snacks, players = [], []
        if pos is not None:
            try:
                raw_players = pos.split("|")[0].split("**")
                raw_snacks = pos.split("|")[1].split("**")
                if raw_players == '':
                    pass
                else:
                    for raw_player in raw_players:
                        raw_positions = raw_player.split("*")
                        if len(raw_positions) == 0:
                            continue

                        positions = []
                        for raw_position in raw_positions:
                            if raw_position == "":
                                continue
                            nums = raw_position.split(')')[0].split('(')[1].split(',')
                            positions.append((int(nums[0]), int(nums[1])))
                        players.append(positions)
                for i in range(len(raw_snacks)):
                    nums = raw_snacks[i].split(')')[0].split('(')[1].split(',')
                    snacks.append((int(nums[0]), int(nums[1])))
            except:
                print("Encountered an error for the position:", pos)
        return snacks, players


def main():
    GameClient()


if __name__ == "__main__":
    main()
