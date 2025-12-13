"""
config.py

Central configuration file for The Floor game.
Contains all configurable game parameters in one place for easy modification.
"""

# Display Settings
SCREEN_WIDTH = 2400
SCREEN_HEIGHT = 1350
FPS = 60

# Grid Layout
GRID_ROWS = 3
GRID_COLS = 3

# Timing Settings (in milliseconds)
DUEL_INITIAL_TIME_MS = 40_000  # 40 seconds per player in duel
RANDOMIZER_TOTAL_DURATION_MS = 7_000  # 7 seconds for randomizer animation
RANDOMIZER_MIN_INTERVAL_MS = 200  # Fastest randomizer switch (0.2 seconds)
RANDOMIZER_MAX_INTERVAL_MS = 700  # Slowest randomizer switch (0.7 seconds)
ANSWER_REVEAL_TIME_MS = 3_000  # 3 seconds to show answer
PASS_PENALTY_TIME_MS = 3_000  # 3 second penalty for passing

# Font Sizes
FLOOR_TITLE_FONT_SIZE = 72
FLOOR_TILE_FONT_SIZE = 40
FLOOR_MESSAGE_FONT_SIZE = 48
DUEL_TIMER_FONT_SIZE = 72
DUEL_NAME_FONT_SIZE = 40
DUEL_ANSWER_FONT_SIZE = 56

# Colors (RGB tuples)
FLOOR_BG_COLOR = (15, 15, 30)        # Dark background
FLOOR_TILE_COLOR = (30, 60, 120)     # Base tile color (dark blue)
FLOOR_HIGHLIGHT_COLOR = (80, 140, 220)  # Highlighted tile color (light blue)
FLOOR_GRID_LINE_COLOR = (10, 20, 40) # Grid outline color
FLOOR_TEXT_COLOR = (255, 255, 255)   # Text color
DUEL_BG_COLOR = (20, 20, 30)         # Duel background color

# Common UI Colors
WHITE = (255, 255, 255)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
GOLD = (255, 215, 0)
GREEN = (0, 150, 0)
LIGHT_BLUE = (173, 216, 230)
BLACK_ALPHA_180 = (0, 0, 0, 180)     # Black with alpha for overlays
BLACK_ALPHA_200 = (0, 0, 0, 200)     # Black with alpha for overlays

# Image Settings
DUEL_IMAGE_WIDTH = 1440
DUEL_IMAGE_HEIGHT = 810

# Layout Settings
FLOOR_TOP_MARGIN = 100
FLOOR_BOTTOM_MARGIN = 100
FLOOR_SIDE_MARGIN = 100
TILE_PADDING = 5

# File Paths
CSV_FILE_PATH = "floor_tiles.csv"
IMAGES_BASE_PATH = "images"