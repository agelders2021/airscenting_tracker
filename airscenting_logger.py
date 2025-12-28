#!/usr/bin/env python3
"""
Air-Scenting Logger
Main application entry point
"""
from ui import AirScentingUI


def main():
    """Main entry point"""
    app = AirScentingUI()
    app.run()


if __name__ == "__main__":
    main()
