"""
main.py

Stitches FloorScreen and DuelScreen together into one app.

Flow:
- Start on FloorScreen (3x3 grid).
- Press SPACE to activate the randomizer.
- When the randomizer finishes, click a tile adjacent to the highlighted one.
- That click triggers:
    * FloorScreen.request_screen_change = "duel"
    * FloorScreen stores challenger/defender info.
- main.py reads that info and constructs a DuelScreen with:
    * challenger_name
    * defender_name
    * defender_category
- DuelScreen runs the duel timers.
- (Optional) Press ENTER in DuelScreen to go back to FloorScreen.
"""

import copy
import csv
import pygame
from floor import FloorScreen
from duel import DuelScreen


def load_tile_data_from_csv(csv_path):
    data = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("name", "").strip()
            category = row.get("category", "").strip()
            if name:
                data.append({"name": name, "category": category})
    return data


def main():
    # Initialize Pygame.
    pygame.init()

    # Create the main window.
    screen = pygame.display.set_mode((1600, 900))
    pygame.display.set_caption("The Floor")

    # Clock for FPS limiting and delta time.
    clock = pygame.time.Clock()

    # Load initial tile data from CSV ONCE
    initial_tile_data = load_tile_data_from_csv("floor_tiles.csv")
    active_tile_data = copy.deepcopy(initial_tile_data)

    # -------------------------
    # Screen / mode setup
    # -------------------------
    # Start on the floor.
    floor_screen = FloorScreen(screen, tile_data=active_tile_data)
    current_screen = floor_screen
    mode = "floor"  # either "floor" or "duel"

    running = True
    while running:
        # delta_ms: milliseconds since last frame.
        delta_ms = clock.tick(60)

        # -------------------------
        # Event handling
        # -------------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                # ESC quits the whole app.
                running = False

            else:
                # Forward all other events to whichever screen is active.
                current_screen.handle_event(event)

        # -------------------------
        # Update & draw
        # -------------------------
        current_screen.update(delta_ms)
        current_screen.draw()
        pygame.display.flip()

        # -------------------------
        # Screen switching logic
        # -------------------------
        if mode == "floor":
            # Check if floor wants to switch to duel.
            if floor_screen.request_screen_change == "duel":
                payload = floor_screen.get_selection_payload()

                if payload is None:
                    # Something went wrong / incomplete selection,
                    # so just ignore for now.
                    print("Warning: FloorScreen requested 'duel' but payload is None.")
                else:
                    # Create DuelScreen with the payload data.
                    duel_screen = DuelScreen(
                        screen,
                        # initial_time_ms=30_000,
                        challenger_name=payload["challenger_name"],
                        defender_name=payload["defender_name"],
                        defender_category=payload["defender_category"],
                    )

                    # Switch active screen & mode.
                    current_screen = duel_screen
                    mode = "duel"

        elif mode == "duel":
            req = current_screen.request_screen_change
            if req:
                if isinstance(req, dict) and req.get("screen") == "floor":
                    winner = req.get("winner")
                    loser = req.get("loser")
                    # Do NOT update active_tile_data yet; wait for SPACE in FloorScreen
                    floor_screen = FloorScreen(screen, winner=winner, loser=loser, tile_data=active_tile_data)
                    current_screen = floor_screen
                    mode = "floor"
                elif req == "floor":
                    floor_screen = FloorScreen(screen, tile_data=active_tile_data)
                    current_screen = floor_screen
                    mode = "floor"

        # After draw, if we're on FloorScreen and just finished the update, sync tile_data
        if mode == "floor" and hasattr(current_screen, "awaiting_update") and not current_screen.awaiting_update and current_screen.winner and current_screen.loser:
            # Copy updated tile data back to active_tile_data
            for i, tile in enumerate(current_screen.tile_data):
                active_tile_data[i]["name"] = tile["name"]
                active_tile_data[i]["category"] = tile["category"]
            # Reset winner/loser so this doesn't repeat
            current_screen.winner = None
            current_screen.loser = None

    pygame.quit()


if __name__ == "__main__":
    main()
