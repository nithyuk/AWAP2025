import sys
import os
import time
import json

"""
Displays a replay in the terminal via ASCII
Sample usage: python3 replay_game_cli.py game_replay.awap25r
"""
# ANSI color codes
COLOR_MAP = {
    "GRASS": "\033[42m ",  # Green background
    "WATER": "\033[46m ",  # Cyan background
    "MOUNTAIN": "\033[47m ",  # White background
    "BRIDGE": "\033[45m ",  # Brown background
    "SAND": "\033[43m ",  # Yellow background
    "BLUE": "\033[44mB",  # Blue background for Blue team
    "RED": "\033[41mR",  # Red background for Red team
    "RESET": "\033[0m",
}


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def render_game_state(game_state, map_data):
    width, height = map_data["width"], map_data["height"]
    tiles = map_data["tiles"]
    grid = [
        [COLOR_MAP[tiles[y][x]] + " " + COLOR_MAP["RESET"] for x in range(width)]
        for y in range(height)
    ]

    # Place buildings
    for team, buildings in game_state["buildings"].items():
        for building in buildings:
            grid[building["y"]][building["x"]] = (
                COLOR_MAP[team] + "C" + COLOR_MAP["RESET"]
            )

    # Place units
    for team, units in game_state["units"].items():
        for unit in units:
            grid[unit["y"]][unit["x"]] = COLOR_MAP[team] + "U" + COLOR_MAP["RESET"]

    # Print the grid
    for row in grid:
        print("".join(row))

    print(
        f"Turn: {game_state['turn']}, Balance: BLUE {game_state['balance']['BLUE']} - RED {game_state['balance']['RED']}"
    )


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 replay_game_cli.py <replay_file>")
        return

    replay_file = sys.argv[1]
    with open(replay_file, "r") as f:
        data = json.load(f)

    map_data = data["map"]
    replay = data["replay"]

    for step in replay:
        clear_screen()
        print(f"Turn {step['turn_number']}")
        render_game_state(step["game_state"], map_data)
        time.sleep(1)

    print(f"Winner: {data['winner_color']}")


if __name__ == "__main__":
    main()
