from src.game import Game
from argparse import ArgumentParser
import json

"""CLI entry point to game"""
def main():

    # command line arguments
    parser = ArgumentParser()

    parser.add_argument(
        "-b", "--blue_path", type=str, required=False, default="bots/attack_bot_v1.py"
    )
    parser.add_argument(
        "-r", "--red_path", type=str, required=False, default="bots/attack_bot_v1.py"
    )

    parser.add_argument(
        "-m", "--map_path", type=str, required=False, default="maps/simple_map.awap25m"
    )

    parser.add_argument("-c", "--config_file", type=str, required=False)

    parser.add_argument(
        "--render",
        action="store_true",
        help="Whether or not to display the game while it is running",
    )

    parser.add_argument( 
        "-o", "--output_file", type=str, required=False, default="replays/game_replay.awap25r" # AWAP format (used for CLI view)
    )

    args = parser.parse_args()

    render = args.render

    # initialize the game
    if not (args.blue_path or not args.red_path) and not args.config_file:
        raise Exception(
            "Must provide --blue_path, --red_path, and --map_path if not using --config_file"
        )

    if args.config_file:
        with open(args.config_file, "r") as f:
            config = json.load(f)
            blue_bot = config["players"][0]["blue"]
            red_bot = config["players"][0]["red"]
            map_name = config["map"]

            blue_path = f"bots/{blue_bot}.py" if not blue_bot.endswith('.py') else f"bots/{blue_bot}"
            red_path = f"bots/{red_bot}.py" if not red_bot.endswith('.py') else f"bots/{red_bot}"
            map_path = f"maps/{map_name}.awap25m" if not map_name.endswith('.awap25m') else f"maps/{map_name}"

            print(f"Blue: {blue_path}, Red: {red_path}, Map: {map_path}")
    else:
        blue_path = args.blue_path
        red_path = args.red_path
        map_path = args.map_path

    game = Game(
        blue_path=blue_path, red_path=red_path, map_path=map_path, output_path=args.output_file, render=render
    )
    print("Game Start")

    game.run_game()


if __name__ == "__main__":
    main()
