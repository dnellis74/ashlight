#!/usr/bin/env python3
# Ash Light - A terminal dungeon crawler

import os
import random
import sys
import termios
import tty
import time
import signal
from rich.console import Console
from rich.text import Text

# Map constants
WIDTH = 40
HEIGHT = 15
VISION_RADIUS = 3
TORCH_RADIUS = 3
TORCH_COUNT = 3

WALL = '#'
FLOOR = '.'
PLAYER = '@'
TREASURE = 'K'  # now represents keys
EXIT = 'E'
TORCH = '!'
FOG = ' '

# Arrow key escape sequences
UP = '\x1b[A'
DOWN = '\x1b[B'
LEFT = '\x1b[D'
RIGHT = '\x1b[C'

# Directions (now using arrow key sequences)
DIRS = {
    UP: (-1, 0),
    DOWN: (1, 0),
    LEFT: (0, -1),
    RIGHT: (0, 1),
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
        self.treasure_pos = [self.random_empty() for _ in range(3)]
        self.collected_treasures = set()
        self.exit_pos = self.random_empty()
        self.has_treasure = False
        self.message = None  # Current game message
        self.message_style = "white"  # Style for the current message
        self.running = True  # Flag to control the game loop

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
                # Always show the player if they're at this position
                if (y, x) == self.player_pos:
                    row.append(PLAYER, style="bold yellow")
                # If tile is currently visible due to torch or player light
                elif self.visible[y][x]:
                    style = self.get_tile_style(y, x)
                    if (y, x) in self.treasure_pos and (y, x) not in self.collected_treasures:
                        row.append(TREASURE, style="bold magenta")
                    elif (y, x) == self.exit_pos:
                        row.append(EXIT, style="bold cyan")
                    elif (y, x) in self.torches:
                        row.append(TORCH, style="bold red")
                    else:
                        tile = self.map[y][x]
                        row.append(tile, style=style)
                # If tile has been seen before, draw it in dim memory
                elif self.seen[y][x]:
                    tile = self.map[y][x]
                    if tile == WALL or tile == FLOOR:
                        row.append(tile, style="grey23")
                    else:
                        row.append(FOG, style="dim")
                # Tile has never been seen
                else:
                    row.append(FOG, style="dim")
            console.print(row)
        console.print(f"[bold]Torches left:[/bold] {self.torch_count}")
        
        # Display game messages in a consistent location
        if self.message:
            console.print(f"[{self.message_style}]{self.message}[/{self.message_style}]")
        elif self.has_treasure:
            console.print("[bold green]You have the treasure! Find the exit![/bold green]")

        # Add controls and legend
        console.print("[dim]Controls: [↑↓←→] move  [A] drop torch  [Ctrl+C] quit[/dim]")
        console.print("[dim]Legend: [bold yellow]@[/bold yellow] you  [bold red]![/bold red] torch  [bold magenta]K[/bold magenta] key  [bold cyan]E[/bold cyan] exit[/dim]")

    def move(self, dy, dx):
        ny, nx = self.player_pos[0] + dy, self.player_pos[1] + dx
        if self.in_bounds(ny, nx) and self.map[ny][nx] != WALL:
            old_pos = self.player_pos
            self.player_pos = (ny, nx)
            
            # Handle key collection
            if self.player_pos in self.treasure_pos and self.player_pos not in self.collected_treasures:
                self.collected_treasures.add(self.player_pos)
                self.set_message(f"You found a key! ({len(self.collected_treasures)}/3)", "bold magenta")
                if len(self.collected_treasures) == 2:
                    self.set_message("You hear a distant wail... Something ancient has stirred.\nThe dead do not rest easy in this place. And now, they know you're here.", "bold red")
                if len(self.collected_treasures) == 3:
                    self.has_treasure = True
                    self.set_message("You have all three keys! The exit is now your only hope.", "bold green")
            
            # Handle exit with treasure
            elif self.player_pos == self.exit_pos and self.has_treasure:
                self.set_message("You escaped with the treasure! Victory!", "bold green")
                time.sleep(2)  # Give player time to see the victory message
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
            if ch == '\x1b':  # Arrow key prefix
                ch += sys.stdin.read(2)  # Read the rest of the arrow key sequence
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
        console.print("[dim italic]Three ghost-guarded keys must be found to unlock the way out.[/dim italic]", justify="center")
        console.print("", justify="center")
        console.print("[bold][Press 'B' to Begin][/bold]", justify="center")
        while True:
            key = self.getch()
            if key == ' ':
                break

    def checkEnter(self, cmd):
        return ord(cmd) in (10, 13)

    def set_message(self, text, style="white"):
        self.message = text
        self.message_style = style

    def handle_sigint(self, signum, frame):
        self.running = False
        console.print("\n[bold red]Game Over![/bold red]")
        sys.exit(0)

def main():
    game = Game()
    signal.signal(signal.SIGINT, game.handle_sigint)
    game.title_screen()
    
    while game.running:
        game.render()
        cmd = game.getch()
        
        if cmd in DIRS:
            game.move(*DIRS[cmd])
        elif game.checkEnter(cmd):
            game.place_torch()

if __name__ == "__main__":
    main()
