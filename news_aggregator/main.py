#!/usr/bin/env python3
# main.py - Entry point for Personal News Aggregator

import sys
import os

# Add the package directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tkinter as tk
from app import NewsAggregatorApp
from dialogs import signal_existing_instance_to_close, start_instance_listener


def main():
    """Main entry point."""
    signal_existing_instance_to_close()
    root = tk.Tk()
    start_instance_listener(root)
    app = NewsAggregatorApp(root)
    # mainloop on the hidden owner (which owns the Toplevel)
    app._owner.mainloop()


if __name__ == "__main__":
    main()
