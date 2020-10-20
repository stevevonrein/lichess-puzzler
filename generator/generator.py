import logging
import json
import time
import argparse
import chess
import chess.pgn
import chess.engine
from chess import Move, Color
from chess.engine import SimpleEngine
from chess.pgn import Game, GameNode
from typing import List, Any, Optional, Tuple, Dict

# Initialize Logging Module
logger = logging.getLogger(__name__)
logging.basicConfig(format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M')
logger.setLevel(logging.DEBUG)
# Uncomment this for very verbose python-chess logging
# logging.basicConfig(level=logging.DEBUG)

get_move_limit = chess.engine.Limit(depth = 20)
has_mate_limit = chess.engine.Limit(depth = 20)

def setup_logging(args: Any) -> None:
    """
    Sets logging module verbosity according to runtime arguments
    """
    if args.verbose:
        if args.verbose == 2:
            logger.setLevel(logging.DEBUG)
        elif args.verbose == 1:
            logger.setLevel(logging.INFO)


def parse_args() -> Any:
    """
    Define an argument parser and return the parsed arguments
    """
    parser = argparse.ArgumentParser(
        prog='generator.py',
        description='takes a pgn file and produces chess puzzles')
    parser.add_argument("--file", "-f", help="input PGN file", required=True, metavar="FILE.pgn")
    parser.add_argument("--engine", "-e", help="analysis engine", default="stockfish")
    parser.add_argument("--threads", "-t", help="count of cpu threads for engine searches", default="4")
    parser.add_argument("--nodb", "-n", help="don't log games to the db", action='store_true')
    parser.add_argument("--verbose", "-v", help="increase verbosity", action="count")

    return parser.parse_args()


def has_mate(engine: SimpleEngine, node: GameNode) -> bool:
    """
    Returns a boolean indicating whether the side to move has a mating line available
    """
    ev = node.eval()
    if not ev or not ev.is_mate():
        return False;

    info = engine.analyse(node.board(), limit = has_mate_limit, multipv = 1)

    return info[0]["score"].is_mate()


def get_only_defensive_move(engine: SimpleEngine, node: GameNode) -> Optional[Move]:
    """
    Get a move for a position presumed to be defending during a mating attack
    """
    logger.debug("Getting defensive move...")
    info = engine.analyse(node.board(), multipv = 2, limit = get_move_limit)

    if not info[0]:
        return None

    if info[1]:
        return None

    return info[0]["pv"][0]


# notes for if I ever refactor this function
#
#   while time.time() <= end_time and threads <= 50:
#       threads = threads+1
#       pmate,mate = determine_mates(..., threads)
#       moves = analyze_mates(pmate,mate,info_handler)
#       if moves is not None:
#           return moves
#   throw TimeoutError
def get_only_mate_move(engine: SimpleEngine, node: GameNode) -> Optional[Move]:
    """
    Takes a GameNode and returns an only moves leading to mate
    """
    logger.debug("Getting only mate move...")
    info = engine.analyse(node.board(), multipv = 2, limit = get_move_limit)

    if not info[0] or not info[0]["score"].is_mate():
        logger.debug("Best move is not a mate")
        return None

    if len(info) > 1 and info[1]["score"].is_mate():
        logger.debug("Second best move is also a mate")
        return None

    return info[0]["pv"][0]


def cook(engine: SimpleEngine, node: GameNode, side_to_mate: Color) -> Optional[List[Move]]:
    """
    Recursively calculate puzzle solution
    """

    if node.board().is_game_over():
        return []

    if node.board().turn == side_to_mate:
        move = get_only_mate_move(engine, node)
    else:
        move = get_only_defensive_move(engine, node)

    if move is None:
        return None

    next_moves = cook(engine, node.add_main_variation(move), side_to_mate)

    if next_moves is None:
        return None

    return [move] + next_moves


def analyze_game(engine: SimpleEngine, game: Game) -> Tuple[Optional[GameNode], Optional[List[Move]]]:
    """
    Evaluate the moves in a game looking for puzzles
    """

    logger.debug("Analyzing game {}...".format(game.headers.get("Site", "?")))

    for node in game.mainline():

        if has_mate(engine, node):
            logger.debug("Mate found on move {}. Probing...".format(node.board().fullmove_number))
            solution = cook(engine, node, node.board().turn)
            if solution:
                return node, solution

    return None, None


def main() -> None:
    args = parse_args()
    setup_logging(args)

    # setup the engine
    enginepath = args.engine
    engine = chess.engine.SimpleEngine.popen_uci(enginepath)
    engine.configure({'Threads': args.threads})

    with open(args.file) as pgn:
        for game in iter(lambda: chess.pgn.read_game(pgn), None):
            header_site = game.headers.get("Site", "?")
            logger.info("{}".format(header_site))

            node, solution = analyze_game(engine, game)

            if node is None or solution is None:
                logger.debug("No only move sequence found.")

            else:

                # Compose and print the puzzle
                logger.info("Printing puzzle...")
                puzzle : Dict[str, Any] = {}
                puzzle["fen"] = node.board().fen()
                puzzle["solution"] = list(map(lambda m : m.uci(), solution))
                puzzle["game_id"] = header_site
                jsondata = json.dumps(puzzle)
                print(jsondata)


if __name__ == "__main__":
    main()

# vim: ft=python expandtab smarttab shiftwidth=4 softtabstop=4 fileencoding=UTF-8: