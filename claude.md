# The Floor — Project Context (claude.md)

## High-Level Goal

This project is a **Pygame-based prototype** of a game inspired by the TV show *The Floor*.

The core gameplay loop is:

1. **Floor Screen**
   - Display a grid of category tiles.
   - Randomly select a tile using a slowing “roulette” animation.
   - Allow the player to choose an *adjacent* tile to challenge.

2. **Duel Screen**
   - Run a timed head-to-head duel between two categories.
   - Alternate active timers with user input.
   - Use category-specific image prompts.

The long-term goal is to support **territory expansion**, where winning duels causes tiles to merge and expand across the grid.

---

## Current Architecture

The game uses a **screen/state pattern**, where each major view is encapsulated in its own class:

```
floor/
│
├── main.py        # Global game loop + screen switching
├── floor.py       # FloorScreen (grid + randomizer)
├── duel.py        # DuelScreen (timers + prompts)
├── utils.py       # Helper functions (create image folders)
├── floor_tiles.csv
└── images/
    └── <category>/
        └── *.jpg
```

### Screen Lifecycle

Each screen implements the same interface:

- `handle_event(event)`
- `update(delta_ms)`
- `draw()`

`main.py` owns:
- the Pygame window
- the main loop
- switching between screens via `request_screen_change`

---

## Gameplay Flow

The full game flow consists of several distinct phases:

### 1. Initial Floor (Randomizer Mode)
- Display 3×3 grid with player names/categories
- User presses **SPACE** to activate randomizer
- Randomizer animation runs for 5 seconds, landing on a tile
- User clicks an **orthogonally adjacent** tile to challenge
- Transition to Duel

### 2. Duel
- Challenger (Player 1) vs Defender (Player 2)
- Each has 10-second timer
- Press **SPACE** to start duel
- Images display from defender's category folder
- Active player can:
  - Press **SPACE** to reveal answer (3s pause, yellow text) → auto-switch to opponent
  - Press **X** to pass (3s time penalty, red text, stay active)
  - Press **P** to pause/unpause
- When timer hits zero, opponent wins
- Press **SPACE** to return to Floor with results

### 3. Post-Duel Floor (Result Display)
- FloorScreen shows: `"Duel ended. Winner: X, Loser: Y. Press SPACE to update the FLOOR!"`
- User presses **SPACE**
- All loser's tiles become winner's tiles (territory expansion)
- Transition to Post-Duel Idle

### 4. Post-Duel Idle (Click-to-Challenge Mode)
- All winner's tiles are highlighted
- Message: `"Press SPACE to ACTIVATE THE RANDOMIZER or click a category to start a challenge!"`
- User can either:
  - Press **SPACE** → return to Randomizer Mode (resets to step 1)
  - Click an **adjacent tile** (not owned by winner) → immediate Duel (winner is challenger)

This cycle repeats, allowing territory to gradually consolidate.

---

## FloorScreen (floor.py)

### Responsibilities

- Render a **3×3 grid** of tiles.
- Load tile metadata from `floor_tiles.csv`:
  - `name`
  - `category`
- Run a **5-second randomizer animation** that:
  - starts fast (~0.2s per tile)
  - slows over time using easing (ease-out quad)
  - lands on a final tile
- After landing:
  - Allow clicking **orthogonally adjacent tiles only**
  - Capture selection metadata
  - Request transition to DuelScreen

### Key State

- `state`: `"idle" | "randomizing" | "finished"`
- `highlighted_index`: current lit tile during randomizer
- `final_tile_index`: tile where randomizer ends
- `selected_origin`: `(row, col)` of challenger tile
- `selected_target`: `(row, col)` of defender tile
- `winner`: name of duel winner (set when returning from DuelScreen)
- `loser`: name of duel loser (set when returning from DuelScreen)
- `awaiting_update`: bool, true when waiting for user to press SPACE to apply duel results
- `post_duel_idle`: bool, true after duel results applied, enables click-to-challenge mode
- `highlighted_indices`: list of indices for all tiles owned by winner (for visual feedback)

### Output to DuelScreen

FloorScreen exposes:

```python
get_selection_payload() -> {
    "challenger_name": str,
    "defender_name": str,
    "defender_category": str
}
```

Where:
- `challenger_name`: the player initiating the duel (randomizer winner or previous duel winner)
- `defender_name`: the opponent being challenged
- `defender_category`: category of the defender (determines which images to show)

This keeps `main.py` decoupled from tile internals.

### Design Note (Future Expansion)

Tiles are represented as `FloorTile` objects with `(row, col)` coordinates.

This is intentional:
- In the future, **merged territories** may span multiple grid cells.
- The adjacency logic and click validation are designed to be replaceable with region-based logic later.

---

## DuelScreen (duel.py)

### Responsibilities

- Display a duel window with:
  - Two countdown timers (Player 1 & Player 2)
  - **Whole seconds precision** (not tenths)
  - Visual highlight for the active player (green box)
  - Player names displayed under each timer
- Display category-specific images loaded from `images/{defender_category}/`
- Image filenames should follow format: `##-Answer.png` (e.g., `01-Taylor Swift.png`)
- Handle duel flow via SPACEBAR:
  - **Before duel starts**: Press SPACE to begin
  - **During duel**: Press SPACE to reveal answer (yellow text, 3s pause)
  - **After answer reveal**: Auto-switches to next player + next image
  - **When time expires**: Press SPACE to return to FloorScreen
- Pause/unpause with **P key** (pauses timer and shows "PAUSED" overlay)
- Pass with **X key** (shows answer in red, applies 3s time penalty, stays with same player)

### Inputs from FloorScreen

DuelScreen is initialized with metadata from FloorScreen:

```python
DuelScreen(
    screen,
    initial_time_ms=10_000,  # default: 10 seconds per player
    challenger_name=...,
    defender_name=...,
    defender_category=...
)
```

These values control:
- `challenger_name`: displayed as Player 1 (top-left)
- `defender_name`: displayed as Player 2 (top-right)
- `defender_category`: determines which image folder to load from
- `initial_time_ms`: starting time for each player's timer

### Output to FloorScreen

When duel ends (timer reaches zero), DuelScreen sets:

```python
request_screen_change = {
    "screen": "floor",
    "winner": <name of winning player>,
    "loser": <name of losing player>
}
```

This allows FloorScreen to apply territory changes (winner takes loser's tile).

---

## main.py

### Responsibilities

- Initialize Pygame (1600×900 window)
- Run the main game loop at 60 FPS
- Maintain `current_screen` and `mode` ("floor" or "duel")
- Load and manage `active_tile_data` from `floor_tiles.csv`
- Forward:
  - events (except ESC/QUIT, which exit the app)
  - delta time updates
  - draw calls
- Handle screen transitions:
  - **Floor → Duel**: When FloorScreen sets `request_screen_change = "duel"`
    - Reads `get_selection_payload()` for challenger/defender metadata
    - Creates new DuelScreen with that metadata
  - **Duel → Floor**: When DuelScreen returns winner/loser
    - Creates new FloorScreen with `winner` and `loser` parameters
    - FloorScreen displays result message and waits for SPACE
    - After SPACE, updates `active_tile_data` to merge tiles
    - Syncs updated data back to main's `active_tile_data`

### Persistent Floor State

`main.py` maintains `active_tile_data` as the source of truth for tile ownership:
- Loaded once from `floor_tiles.csv` at startup
- Passed to FloorScreen on each instantiation
- Updated after duel results are applied
- **Not** written back to CSV (in-memory only during session)

`main.py` intentionally contains **no game logic** beyond orchestration.

---

## Technical Constraints & Intentions

- **Pygame-only**, desktop-focused (no iOS / mobile target).
- No Docker or containerization required.
- Emphasis on:
  - clarity
  - modularity
  - ease of iteration
- This is a **prototype**, not a performance-optimized engine.

---

## Current Status

**Completed:**
- ✅ DuelScreen displays player names and categories
- ✅ Images loaded from category folders
- ✅ Duel resolution (win/loss based on timer expiration)
- ✅ Territory expansion (winner takes loser's tile)
- ✅ Post-duel flow (result display → SPACE to update → click-to-challenge mode)
- ✅ Answer reveal system (parsed from image filenames)
- ✅ Pause and pass functionality

**Known Limitations:**
- Floor state is in-memory only (not persisted to CSV between sessions)
- No validation for missing image folders or categories
- Some categories in CSV (News, Music) don't have corresponding image folders
- Click-to-challenge mode only works for directly adjacent tiles (no region-based logic yet)

**Potential Next Steps:**
- Add scoring/round tracking
- Support for larger grids (beyond 3×3)
- More sophisticated territory merging (regions spanning multiple tiles)
- Persistent floor state across sessions
- UI polish (animations, sound effects)

---

## Design Philosophy

- Prefer explicit state over clever abstractions.
- Keep screens isolated and testable.
- Make future expansion (merged tiles, larger grids, scoring rules) straightforward.

---

## File Formats & Conventions

### floor_tiles.csv

CSV format with two columns:
```csv
name,category
Keith,Nature
Lori,STEM
Bernie,Entertainment
...
```

- **name**: Player/tile identifier (displayed on tile)
- **category**: Category for that tile (must match an image folder)
- Must have at least 9 rows for 3×3 grid (extras are ignored)

### Image Organization

Images are organized by category:
```
images/
├── Nature/
│   ├── 01-Peppers.jpg
│   ├── 02-Broccoli.jpg
│   └── 03-Coffee Beans.jpg
├── STEM/
│   └── ...
└── Entertainment/
    └── ...
```

**Image filename format**: `##-Answer.extension`
- `##`: Two-digit number (for sorting)
- `Answer`: The correct answer text (displayed when revealed)
- Extension: `.jpg`, `.png`, `.jpeg`, `.bmp`, or `.gif`

Example: `01-Taylor Swift.png` → answer revealed as "Taylor Swift"

Images are automatically scaled to 1120×630 pixels.

### Categories

Currently defined categories (based on floor_tiles.csv):
- Nature
- STEM
- Entertainment
- News (⚠️ missing image folder)
- Music (⚠️ missing image folder)
- Physical
- World
- Lifestyle
- Wildcard

**Note**: If a category folder is missing, DuelScreen will only show placeholder starter/ending images.

---

This file should be treated as **authoritative context** when modifying or extending the codebase.
