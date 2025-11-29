"""
floor.py

Defines the FloorScreen class for a "The Floor"-style grid:

- 3x3 grid of tiles.
- Each tile uses text loaded from a CSV (columns: name, category).
- Top title text: "THE FLOOR!"
- Bottom message: "Press Spacebar to ACTIVATE THE RANDOMIZER".

Behavior:
- SPACE starts a 10-second "randomizer" animation:
    * A highlight moves from tile to tile.
    * It starts fast and slows down over time (ease-out feel).
    * At the end, it lands on one final tile (highlight stays).

- After the randomizer ends:
    * Player can click any tile that is ORTHOGONALLY ADJACENT
      (up, down, left, right) to the final tile.
    * A valid click sets:
          self.request_screen_change = "duel"
          self.selected_origin = (row, col) of final tile
          self.selected_target = (row, col) of clicked neighbor

The idea is to keep the grid logic modular enough
to support future "merged squares" / territories.
"""

import csv
import random
from dataclasses import dataclass

import pygame


# ---------------------------------------------------------
# DATA STRUCTURE: tile representation
# ---------------------------------------------------------

@dataclass
class FloorTile:
    """
    Represents one logical tile on the floor grid.

    For now, each tile is exactly one cell in a 3x3 grid.
    In the future, you can extend this to represent merged regions:
    - e.g. a tile that spans multiple (row, col) coordinates.

    Attributes:
        row, col: integer grid position (0-based).
        rect: pygame.Rect describing where it is drawn on screen.
        name: text to show inside tile (from CSV).
        category: extra data from CSV (for future use).
    """
    row: int
    col: int
    rect: pygame.Rect
    name: str
    category: str


class FloorScreen:
    """
    FloorScreen encapsulates the main floor grid and randomizer behavior.
    """

    def __init__(self, screen, csv_path="floor_tiles.csv", rows=3, cols=3, winner=None, loser=None, tile_data=None):
        """
        :param screen: the main Pygame display Surface (from set_mode).
        :param csv_path: path to CSV file with columns: name, category.
        :param rows: number of grid rows.
        :param cols: number of grid columns.
        """
        self.screen = screen
        self.width, self.height = self.screen.get_size()
        self.rows = rows
        self.cols = cols

        # Fonts: one for title, one for tile text, one for the bottom message.
        self.title_font = pygame.font.SysFont(None, 72)
        self.tile_font = pygame.font.SysFont(None, 32)
        self.message_font = pygame.font.SysFont(None, 36)

        # Colors (RGB tuples)
        self.bg_color = (15, 15, 30)          # dark background
        self.tile_color = (30, 60, 120)       # base tile color (dark-ish blue)
        self.highlight_color = (80, 140, 220) # "lit up" tile color (light blue)
        self.grid_line_color = (10, 20, 40)   # subtle outline
        self.text_color = (255, 255, 255)

        # Use provided tile_data if present, else load from CSV
        if tile_data is not None:
            self.tile_data = tile_data
        else:
            self.tile_data = self._load_tile_data(csv_path)

        # Build the visual grid (positions + rects).
        self.tiles = self._build_tiles()

        # ---------------------------
        # Randomizer state
        # ---------------------------
        self.state = "idle"  # "idle" | "randomizing" | "finished"

        # Index (into self.tiles list) of currently highlighted tile.
        # None when idle and no tile is selected.
        self.highlighted_index = None

        # When the randomizer started (ms since pygame.init()).
        self.random_start_time = None

        # When the next "jump" to a new tile should occur (ms since pygame.init()).
        self.next_switch_time = None

        # Total duration of the randomizer in milliseconds (10 seconds).
        self.random_total_duration = 5_000

        # Minimum and maximum intervals between jumps (ms).
        # We start near min_interval and ease toward max_interval as time passes.
        self.min_interval = 200   # 0.2 seconds
        self.max_interval = 700   # 0.7 seconds (slower near the end)

        # After randomizer ends, we treat the final highlight as origin.
        self.final_tile_index = None

        # Screen-change mechanism (for main.py to inspect).
        self.request_screen_change = None

        # For future logic / DuelScreen communication:
        self.selected_origin = None   # (row, col) of final tile
        self.selected_target = None   # (row, col) of clicked neighbor

        # Winner/loser handling (for DuelScreen result display).
        self.winner = winner
        self.loser = loser
        self.awaiting_update = bool(winner and loser)
        self.duel_message = None
        if self.awaiting_update:
            self.duel_message = f"Duel ended. Winner: {winner}, Loser: {loser}\nPress SPACE to update the FLOOR!"

    # ---------------------------------------------------------
    # CSV loading + grid construction
    # ---------------------------------------------------------

    def _load_tile_data(self, csv_path):
        """
        Load tile name/category data from a CSV file.

        Expected columns: name, category

        Returns a list of dicts: [{"name": ..., "category": ...}, ...]
        """
        data = []
        try:
            with open(csv_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row.get("name", "").strip()
                    category = row.get("category", "").strip()
                    if name:  # only add rows that have a name
                        data.append({"name": name, "category": category})
        except FileNotFoundError:
            # If file is missing, create placeholder data.
            print(f"Warning: CSV file {csv_path} not found. Using placeholder tiles.")
            data = [
                {"name": f"Tile {i + 1}", "category": "Placeholder"}
                for i in range(self.rows * self.cols)
            ]

        # Ensure we have at least rows*cols entries.
        needed = self.rows * self.cols
        if len(data) < needed:
            # Repeat entries if not enough.
            repeats = (needed // max(1, len(data))) + 1
            data = (data * repeats)[:needed]
        else:
            # Trim extras if too many.
            data = data[:needed]

        return data

    def _build_tiles(self):
        """
        Create FloorTile objects with proper positions and rects.

        We want the grid centered in the middle of the screen,
        with some vertical space reserved for the title at the top
        and the message at the bottom.
        """
        tiles = []

        # Margins for top/bottom text areas.
        top_margin = 100
        bottom_margin = 100

        # Available height for the grid area.
        grid_height_available = self.height - top_margin - bottom_margin
        grid_width_available = self.width - 100  # some side margin

        # Size of each cell (square), using the limiting dimension.
        cell_size = min(
            grid_width_available // self.cols,
            grid_height_available // self.rows
        )

        # Compute total grid dimensions actually used.
        grid_width = cell_size * self.cols
        grid_height = cell_size * self.rows

        # Top-left corner of the grid so that it is centered horizontally
        # and positioned between top_margin and bottom_margin vertically.
        grid_left = (self.width - grid_width) // 2
        grid_top = top_margin + (grid_height_available - grid_height) // 2

        # Small padding between tiles so they don't fully touch.
        padding = 5

        index = 0
        for row in range(self.rows):
            for col in range(self.cols):
                x = grid_left + col * cell_size + padding
                y = grid_top + row * cell_size + padding
                w = cell_size - 2 * padding
                h = cell_size - 2 * padding
                rect = pygame.Rect(x, y, w, h)

                tile_info = self.tile_data[index]
                tile = FloorTile(
                    row=row,
                    col=col,
                    rect=rect,
                    name=tile_info["name"],
                    category=tile_info["category"],
                )
                tiles.append(tile)
                index += 1

        return tiles

    # ---------------------------------------------------------
    # Helper functions
    # ---------------------------------------------------------

    @staticmethod
    def _ease_out_quad(t):
        """
        Simple ease-out curve using a quadratic function.

        :param t: progress from 0.0 to 1.0
        :return: eased value (0.0 to 1.0)

        This gives us fast changes at the start,
        and slower changes near the end.
        """
        t = max(0.0, min(1.0, t))  # clamp to [0, 1]
        return t * t  # feel free to adjust to t*(2-t) or similar if you want

    def _pick_next_tile_index(self, current_index):
        """
        Pick a random tile index different from current_index.
        """
        if len(self.tiles) <= 1:
            return 0
        while True:
            idx = random.randrange(len(self.tiles))
            if idx != current_index:
                return idx

    @staticmethod
    def _are_orthogonally_adjacent(tile_a: FloorTile, tile_b: FloorTile) -> bool:
        """
        Returns True if tile_b is orthogonally adjacent (up/down/left/right)
        to tile_a on the grid.

        This uses the difference in row/col:
            - Up:    (row-1, col)
            - Down:  (row+1, col)
            - Left:  (row, col-1)
            - Right: (row, col+1)

        (No diagonals. If you want diagonals, change this.)
        """
        dr = abs(tile_a.row - tile_b.row)
        dc = abs(tile_a.col - tile_b.col)
        return (dr + dc) == 1  # exactly one step horizontally or vertically

    # ---------------------------------------------------------
    # Public API: handle_event, update, draw
    # ---------------------------------------------------------

    def handle_event(self, event):
        """
        Handle a single Pygame event.

        :param event: a Pygame event object.
        """
        if self.awaiting_update and event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            self._replace_loser_with_winner()
            self.awaiting_update = False
            self.duel_message = None
            # Set a new message for post-duel idle state
            self.post_duel_idle = True
            return
        # Allow click-to-challenge in idle state after a duel update
        if hasattr(self, 'post_duel_idle') and self.post_duel_idle and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._handle_click_to_challenge(event.pos)
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE and self.state == "idle":
                self.state = "idle"
                if hasattr(self, 'post_duel_idle'):
                    self.post_duel_idle = False
                self._start_randomizer()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and self.state == "finished":
                self._handle_click(event.pos)

    def _start_randomizer(self):
        """
        Initialize the randomizer state when SPACE is pressed.
        """
        if not self.tiles:
            return

        self.state = "randomizing"
        self.random_start_time = pygame.time.get_ticks()

        # Start by highlighting a random tile.
        self.highlighted_index = random.randrange(len(self.tiles))

        # Schedule the first switch.
        self.next_switch_time = self.random_start_time + self.min_interval

        # We don't yet know the final tile; will be set when animation ends.
        self.final_tile_index = None

    def _handle_click(self, mouse_pos):
        """
        Handle a mouse click when the state is 'finished'.

        Allows clicking any tile that is orthogonally adjacent
        to the final highlighted tile.

        If a valid tile is clicked, set request_screen_change = "duel"
        and record origin/target positions.
        """
        if self.final_tile_index is None:
            return

        final_tile = self.tiles[self.final_tile_index]

        # Find which tile (if any) the user clicked.
        clicked_tile = None
        for tile in self.tiles:
            if tile.rect.collidepoint(mouse_pos):
                clicked_tile = tile
                break

        if clicked_tile is None:
            return  # clicked outside any tile

        # Check adjacency (up/down/left/right).
        if self._are_orthogonally_adjacent(final_tile, clicked_tile):
            # Record positions for the next screen (DuelScreen, etc.).
            self.selected_origin = (final_tile.row, final_tile.col)
            self.selected_target = (clicked_tile.row, clicked_tile.col)
            self.request_screen_change = "duel"
            print("Transitioning to DuelScreen from FloorScreen.")
            print(f"Origin tile: {self.selected_origin}, Target tile: {self.selected_target}")
        else:
            # Not adjacent; ignore or give visual feedback in the future.
            print("Clicked tile is not adjacent to the final tile. Ignoring.")

    def _handle_click_to_challenge(self, mouse_pos):
        clicked_tile = None
        for tile in self.tiles:
            if tile.rect.collidepoint(mouse_pos):
                clicked_tile = tile
                break
        if clicked_tile is None:
            return
        my_tiles = [self.tiles[i] for i in getattr(self, 'highlighted_indices', [])]
        for my_tile in my_tiles:
            if self._are_orthogonally_adjacent(my_tile, clicked_tile) and clicked_tile.name != self.winner:
                self.selected_origin = (my_tile.row, my_tile.col)
                self.selected_target = (clicked_tile.row, clicked_tile.col)
                # Set winner as challenger for get_selection_payload
                self._pending_challenger = self.winner
                self.request_screen_change = "duel"
                print(f"Challenge: {self.winner} (challenger) vs {clicked_tile.name} (defender)")
                return
        print("Clicked tile is not adjacent to any of your tiles or is your own tile.")

    def get_selection_payload(self):
        if self.request_screen_change != "duel":
            return None
        # helper to find a tile by (row, col)
        def find_tile_by_pos(pos):
            row, col = pos
            for tile in self.tiles:
                if tile.row == row and tile.col == col:
                    return tile
            return None
        challenger_tile = find_tile_by_pos(self.selected_origin)
        defender_tile = find_tile_by_pos(self.selected_target)
        if challenger_tile is None or defender_tile is None:
            return None
        # Use _pending_challenger if set (for click-to-challenge), else use tile name
        challenger_name = getattr(self, '_pending_challenger', challenger_tile.name)
        if hasattr(self, '_pending_challenger'):
            del self._pending_challenger
        return {
            "challenger_name": challenger_name,
            "defender_name": defender_tile.name,
            "defender_category": defender_tile.category,
        }



    def update(self, delta_ms):
        """
        Update the floor state.

        :param delta_ms: time since last frame (in ms) from clock.tick().
                         (We mostly rely on pygame.time.get_ticks() for the randomizer.)
        """
        if self.state == "randomizing":
            now = pygame.time.get_ticks()
            elapsed = now - self.random_start_time

            if elapsed >= self.random_total_duration:
                # Randomizer finished; lock in the final tile.
                self.state = "finished"
                self.final_tile_index = self.highlighted_index
                return

            # If it's time to switch to another tile, do so.
            if now >= self.next_switch_time:
                # Compute progress in [0, 1].
                t = elapsed / self.random_total_duration

                # Ease-out curve for interval growth.
                eased = self._ease_out_quad(t)

                # Current interval between switches, from min_interval to max_interval.
                current_interval = int(
                    self.min_interval + (self.max_interval - self.min_interval) * eased
                )

                # Choose a new tile index different from the current one.
                self.highlighted_index = self._pick_next_tile_index(self.highlighted_index)

                # Schedule the next switch.
                self.next_switch_time = now + current_interval

        # If state is "idle" or "finished", nothing time-based happens here for now.
        # Future: you could animate UI, show prompts, etc.


    def draw(self):
        """
        Draw the entire floor view onto self.screen.
        """
        # Clear background.
        self.screen.fill(self.bg_color)

        # ----------------------------
        # Draw duel message if present
        # ----------------------------
        if self.duel_message:
            lines = self.duel_message.split("\n")
            for i, line in enumerate(lines):
                msg_surf = self.message_font.render(line, True, (255, 255, 0))
                msg_rect = msg_surf.get_rect(center=(self.width // 2, self.height - 40 - (len(lines)-i-1)*40))
                self.screen.blit(msg_surf, msg_rect)

        # ----------------------------
        # Draw title at top: "THE FLOOR!"
        # ----------------------------
        title_surf = self.title_font.render("THE FLOOR!", True, self.text_color)
        title_rect = title_surf.get_rect(center=(self.width // 2, 50))
        self.screen.blit(title_surf, title_rect)

        # ----------------------------
        # Draw tiles
        # ----------------------------
        for index, tile in enumerate(self.tiles):
            # Highlight all winner's tiles in post-duel idle
            if hasattr(self, 'post_duel_idle') and self.post_duel_idle and hasattr(self, 'highlighted_indices') and index in self.highlighted_indices:
                color = self.highlight_color
            elif index == self.highlighted_index:
                color = self.highlight_color
            else:
                color = self.tile_color

            # Draw filled rectangle for the tile.
            pygame.draw.rect(self.screen, color, tile.rect)

            # Optional: draw a subtle border/outline.
            pygame.draw.rect(self.screen, self.grid_line_color, tile.rect, width=2)

            # Draw tile text: name (and maybe category) centered.
            # For now we draw the name and category stacked vertically if category exists.
            lines = [tile.name]
            if tile.category:
                lines.append(tile.category)

            # Render each line.
            line_surfs = [
                self.tile_font.render(line, True, self.text_color)
                for line in lines
            ]

            # Compute total text height so we can center it block-wise.
            total_text_height = sum(surf.get_height() for surf in line_surfs)
            start_y = tile.rect.centery - total_text_height // 2

            for surf in line_surfs:
                rect = surf.get_rect(center=(tile.rect.centerx, start_y + surf.get_height() // 2))
                self.screen.blit(surf, rect)
                start_y += surf.get_height()

        # ----------------------------
        # Draw bottom message
        # ----------------------------
        if self.duel_message:
            lines = self.duel_message.split("\n")
            for i, line in enumerate(lines):
                msg_surf = self.message_font.render(line, True, (255, 255, 0))
                msg_rect = msg_surf.get_rect(center=(self.width // 2, self.height - 40 - (len(lines)-i-1)*40))
                self.screen.blit(msg_surf, msg_rect)
        elif hasattr(self, 'post_duel_idle') and self.post_duel_idle:
            message = "Press SPACE to ACTIVATE THE RANDOMIZER or click a category to start a challenge!"
            message_surf = self.message_font.render(message, True, self.text_color)
            message_rect = message_surf.get_rect(center=(self.width // 2, self.height - 40))
            self.screen.blit(message_surf, message_rect)
        else:
            if self.state == "idle":
                message = "Press SPACE to ACTIVATE THE RANDOMIZER"
            elif self.state == "randomizing":
                message = "Randomizing..."
            else:  # finished
                message = "Click a tile adjacent to the highlighted one!"

            message_surf = self.message_font.render(message, True, self.text_color)
            message_rect = message_surf.get_rect(center=(self.width // 2, self.height - 40))
            self.screen.blit(message_surf, message_rect)

    def _replace_loser_with_winner(self):
        winner_tile = next((t for t in self.tiles if t.name == self.winner), None)
        for tile in self.tiles:
            if tile.name == self.loser and winner_tile:
                tile.name = self.winner
                tile.category = winner_tile.category
                break
        # After update, highlight all winner's tiles
        self.highlighted_indices = [i for i, t in enumerate(self.tiles) if t.name == self.winner]
        # No CSV write here; in-memory only

    def _save_tiles_to_csv(self):
        pass  # No-op, CSV is not updated during runtime
