#!/usr/bin/env python3
"""Build script to package Realms of Mythos as a standalone desktop executable."""

import PyInstaller.__main__
import sys
import os

def build():
    """Build the executable."""
    PyInstaller.__main__.run([
        'main.py',
        '--name=RealmsOfMythos',
        '--onefile',
        '--windowed',
        '--noconfirm',
        '--clean',
        '--add-data=src:src',
    ])
    print("\nBuild complete! Executable is in the 'dist' folder.")
    print("Run: ./dist/RealmsOfMythos")

if __name__ == "__main__":
    build()
