#!/usr/bin/env python3
"""Realms of Mythos - A Fantasy RPG Adventure."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.game import Game


def main():
    """Entry point."""
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
