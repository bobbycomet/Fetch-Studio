#!/usr/bin/env python3
"""Fetch Studio launcher (also the PyInstaller entry point): python3 run.py  or  python3 -m fetchstudio"""
import sys
from fetchstudio.mainwindow import main
if __name__ == "__main__": sys.exit(main())
