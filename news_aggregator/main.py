#!/usr/bin/env python3
# main.py - Entry point for Personal News Aggregator

import sys
import os

# Add the package directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tkinter as tk
from app import NewsAggregatorApp


def main():
    """Main entry point."""
    root = tk.Tk()

    # Set app icon if available
    try:
        # On Windows, you could set an icon here
        # root.iconbitmap('icon.ico')
        pass
    except tk.TclError:
        pass

    app = NewsAggregatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
