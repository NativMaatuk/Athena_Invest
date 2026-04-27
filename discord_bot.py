"""
Backward-compatible entrypoint for the Discord bot runtime.
The production implementation lives in src/app/bot.py.
"""

from src.app.bot import main


if __name__ == "__main__":
    main()
