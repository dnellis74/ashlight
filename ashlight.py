# Ash Light - A terminal dungeon crawler

import os
import random
import sys
import termios
import tty
import time
from rich.console import Console
from rich.text import Text

# Map constants
WIDTH = 20
HEIGHT = 10
VISION_RADIUS = 3
TORCH_RADIUS = 3
TORCH_COUNT = 3

WALL = '#'
FLOOR = '.'
PLAYER = '@'
TREASURE = 'T'
EXIT = 'E'
TORCH = '!'
FOG = ' '

# Directions
DIRS = {
    'w': (-1, 0),
    's': (1, 0),
    'a': (0, -1),
    'd': (0, 1),
}

console = Console()

class Game:
    def __init__(self):
        self.map = self.generate_map()
        self.visible = [[False] * WIDTH for _ in range(HEIGHT)]
        self.light_levels = [[0] * WIDTH for _ in range(HEIGHT)]
        self.seen = [[False] * WIDTH for _ in range(HEIGHT)]
        self.torches = [(None, None)]  # Placeholder to simulate starting with player light
        self.torch_count = TORCH_COUNT
        self.player_pos = None
        self.treasure_pos = None
        self.exit_pos = None
        self.player_pos = self.random_empty()
        self.treasure_pos = self.random_empty()
        self.exit_pos = self.random_empty()
        self.has_treasure = False

    def generate_map(self):
        grid = [[FLOOR for _ in range(WIDTH)] for _ in range(HEIGHT)]
        for y in range(HEIGHT):
            for x in range(WIDTH):
                if x == 0 or x == WIDTH - 1 or y == 0 or y == HEIGHT - 1:
                    grid[y][x] = WALL
                elif random.random() < 0.1:
                    grid[y][x] = WALL
        return grid

    def random_empty(self):
        while True:
            y = random.randint(1, HEIGHT - 2)
            x = random.randint(1, WIDTH - 2)
            occupied = [pos for pos in [self.player_pos, self.treasure_pos, self.exit_pos] if pos is not None]
            if self.map[y][x] == FLOOR and (y, x) not in occupied:
                return (y, x)

    def in_bounds(self, y, x):
        return 0 <= y < HEIGHT and 0 <= x < WIDTH

    def update_visibility(self):
        self.visible = [[False] * WIDTH for _ in range(HEIGHT)]
        self.light_levels = [[0] * WIDTH for _ in range(HEIGHT)]

        def light_radius(center, radius, flicker=False):
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    ny, nx = center[0] + dy, center[1] + dx
                    if self.in_bounds(ny, nx):
                        dist = abs(dy) + abs(dx)
                        if dist <= radius:
                            self.visible[ny][nx] = True
                            self.seen[ny][nx] = True
                            intensity = max(0, radius - dist)
                            if flicker and random.random() < 0.2:
                                intensity = max(0, intensity - 1)
                            self.light_levels[ny][nx] = max(self.light_levels[ny][nx], intensity)

        for t in self.torches:
            if t == (None, None):  # Player's own light
                if self.torch_count > 0:
                    light_radius(self.player_pos, VISION_RADIUS, flicker=True)
            else:
                light_radius(t, TORCH_RADIUS, flicker=True)

    def get_tile_style(self, y, x):
        brightness = self.light_levels[y][x]
        if brightness == 0:
            return "dim"
        elif self.map[y][x] == WALL:
            return ["grey50", "red3", "dark_red", "bold red"][brightness]
        elif self.map[y][x] == FLOOR:
            return ["grey50", "red3", "dark_red", "bold red"][brightness]
        else:
            return "white"

    def render(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        console.print("[bold]Ash Light[/bold] - Find the treasure and escape. Don't lose your last light.\n")
        self.update_visibility()
        for y in range(HEIGHT):
            row = Text()
            for x in range(WIDTH):
                if self.visible[y][x]:
                    style = self.get_tile_style(y, x)
                    if (y, x) == self.player_pos:
                        row.append(PLAYER, style="bold yellow")
                    elif (y, x) == self.treasure_pos and not self.has_treasure:
                        row.append(TREASURE, style="bold magenta")
                    elif (y, x) == self.exit_pos:
                        row.append(EXIT, style="bold cyan")
                    elif (y, x) in self.torches:
                        row.append(TORCH, style="bold red")
                    else:
                        tile = self.map[y][x]
                        row.append(tile, style=style)
                elif self.seen[y][x]:
                    tile = self.map[y][x]
                    if tile == WALL or tile == FLOOR:
                        row.append(tile, style="grey23")
                    else:
                        row.append(FOG, style="dim")
                else:
                    row.append(FOG, style="dim")
            console.print(row)
        console.print(f"[bold]Torches left:[/bold] {self.torch_count}")
        if self.has_treasure:
            console.print("[bold green]You have the treasure! Find the exit![/bold green]")

        # Add controls and legend
        console.print("[dim]Controls: [WASD] move  [T] or [Enter] drop torch  [Q] quit[/dim]")
        console.print("[dim]Legend: [bold yellow]@[/bold yellow] you  [bold red]![/bold red] torch  [bold magenta]T[/bold magenta] treasure  [bold cyan]E[/bold cyan] exit[/dim]")

    def move(self, dy, dx):
        ny, nx = self.player_pos[0] + dy, self.player_pos[1] + dx
        if self.in_bounds(ny, nx) and self.map[ny][nx] != WALL:
            self.player_pos = (ny, nx)
            if self.player_pos == self.treasure_pos:
                self.has_treasure = True
            elif self.player_pos == self.exit_pos and self.has_treasure:
                self.render()
                console.print("[bold green]You escaped with the treasure! Victory![/bold green]")
                sys.exit(0)

    def place_torch(self):
        if self.torch_count > 0 and self.player_pos not in self.torches:
            self.torches.append(self.player_pos)
            self.torch_count -= 1
            if self.torch_count == 0:
                self.torches = [t for t in self.torches if t != (None, None)]

    def getch(self):
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

    def title_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        console.print("[bold bright_white]Ash Light[/bold bright_white]", justify="center")
        console.print("", justify="center")
        console.print("[dim italic]The fire is fading...[/dim italic]", justify="center")
        console.print("[dim italic]You descend with only a few embers in hand.[/dim italic]", justify="center")
        console.print("[dim italic]Each light you leave behind is one step closer to the dark.[/dim italic]", justify="center")
        console.print("", justify="center")
        console.print("[bold][Press Space to Begin][/bold]", justify="center")
        while True:
            key = self.getch()
            if key == ' ':
                break

    def run(self):
        self.title_screen()
        while True:
            self.render()
            cmd = self.getch().lower()
            if cmd in DIRS:
                self.move(*DIRS[cmd])
            elif cmd == 't' or cmd == '\r':
                self.place_torch()
            elif cmd == 'q':
                print("Goodbye.")
                break

if __name__ == '__main__':
    Game().run()
