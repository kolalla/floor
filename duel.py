"""
duel.py

Defines the DuelScreen class for a "The Floor"-style duel:

- Two countdown timers (player 1 & player 2) with tenths of a second.
- A center "image" that changes when SPACE is pressed.
- SPACE also switches which player's timer is active.

This file does NOT create the game window or main loop by itself.
It expects a main script (e.g. main.py) to:
    - create the Pygame display surface
    - create a DuelScreen instance
    - call handle_event(), update(), draw() each frame
"""

import pygame
import os


class DuelScreen:
    """
    DuelScreen encapsulates all logic and drawing for the duel view.

    The outside world only needs to:
      - create it with a Pygame Surface (the window)
      - call handle_event(event) for each Pygame event
      - call update(delta_ms) each frame
      - call draw() each frame

    It also exposes a 'request_screen_change' attribute that higher-level
    code (like main.py) can read to know if the user wants to switch screens.
    """

    def __init__(
        self,
        screen,
        initial_time_ms=10_000,
        challenger_name=None,
        defender_name=None,
        defender_category=None,
    ):
        self.screen = screen
        self.width, self.height = self.screen.get_size()

        self.initial_time_ms = initial_time_ms
        self.remaining_ms = {1: initial_time_ms, 2: initial_time_ms}
        self.active_player = 1

        self.last_tick = pygame.time.get_ticks()
        self.font = pygame.font.SysFont(None, 64)
        self.name_font = pygame.font.SysFont(None, 36)
        self.answer_font = pygame.font.SysFont(None, 48)

        # Store meta-info coming from the FloorScreen:
        self.challenger_name = challenger_name
        self.defender_name = defender_name
        self.defender_category = defender_category
        self.names_dict = {
            1: challenger_name,
            2: defender_name,
        }

        # Pause functionality
        self.paused = False

        # Answer reveal state
        self.reveal_answer_mode = False
        self.reveal_timer_ms = 0
        self.current_answer = ""

        # Pass penalty state
        self.pass_penalty_mode = False
        self.pass_penalty_timer_ms = 0

        # Print to console
        print(
            "DuelScreen initialized with:"
            "\n\tchallenger_name    =", challenger_name,
            "\n\tdefender_name      =", defender_name,
            "\n\tdefender_category  =", defender_category
        )

        self.images, self.image_filenames = self._load_images_from_folder(f"images/{defender_category}")
        self.current_image_index = 0

        self.winner = None  # 1 or 2 when someone wins, else None
        self.loser = None
        self.request_screen_change = None

        self.started = False

    # ------------------------------------------------------------------
    # INTERNAL HELPERS
    # ------------------------------------------------------------------

    def _create_starter_image(self):
        """
        Create a placeholder image before duel begins.
        Returns a single Surface.
        """
        surf = pygame.Surface((1120, 630), pygame.SRCALPHA)
        surf.fill((173, 216, 230))  # light blue

        # Fill with text
        label = self.font.render(f"Press SPACE to start the duel!", True, (0, 0, 0))
        label_rect = label.get_rect(center=(
            surf.get_width() // 2,
            surf.get_height() // 2)
        )
        surf.blit(label, label_rect)

        return surf 
    
    def _create_ending_image(self, winner):
        """
        Create a placeholder image after duel ends.
        Returns a single Surface.
        """
        surf = pygame.Surface((1120, 630), pygame.SRCALPHA)
        surf.fill((173, 216, 230))  # light blue

        # Split the message into lines
        lines = [
            f"{winner} wins!",
            "Press SPACE to return to the FLOOR!"
        ]

        # Render each line and blit it, centered vertically
        total_height = 0
        rendered_lines = []
        for line in lines:
            label = self.font.render(line, True, (0, 0, 0))
            rendered_lines.append(label)
            total_height += label.get_height()

        # Calculate starting y to center the block of text
        start_y = (surf.get_height() - total_height) // 2

        for label in rendered_lines:
            label_rect = label.get_rect(centerx=surf.get_width() // 2, y=start_y)
            surf.blit(label, label_rect)
            start_y += label.get_height()

        return surf 

    def _load_images_from_folder(self, folder_path):
        """
        Loads all image files from the given folder and returns a tuple of:
        (list of Surfaces, list of filenames)
        """
        images = []
        filenames = []

        images.append(self._create_starter_image())
        filenames.append(None)  # No filename for starter image

        if not os.path.isdir(folder_path):
            print(f"Image folder not found: {folder_path}")
            return images, filenames

        for filename in sorted(os.listdir(folder_path)):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                full_path = os.path.join(folder_path, filename)
                try:
                    img = pygame.image.load(full_path).convert_alpha()
                    img = pygame.transform.smoothscale(img, (1120, 630))
                    images.append(img)
                    filenames.append(filename)
                except Exception as e:
                    print(f"Failed to load image {full_path}: {e}")
        return images, filenames

    @staticmethod
    def _format_time(ms: int) -> str:
        """
        Convert milliseconds to seconds format (whole seconds only).

        Example:
            30450 ms -> "30"
        """
        ms = max(0, ms)  # prevent negative values

        total_seconds = ms // 1000

        return f"{total_seconds}"

    @staticmethod
    def _parse_answer_from_filename(filename):
        """
        Parse the answer from a filename with format: ##-Answer.png

        Example:
            "01-Taylor Swift.png" -> "Taylor Swift"
        """
        if not filename:
            return ""

        # Remove file extension
        name_without_ext = os.path.splitext(filename)[0]

        # Split on '-' and take everything after the first part
        parts = name_without_ext.split('-', 1)
        if len(parts) > 1:
            return parts[1].strip()

        return name_without_ext.strip()

    # ------------------------------------------------------------------
    # PUBLIC INTERFACE
    # ------------------------------------------------------------------

    def handle_event(self, event):
        """
        Process a single Pygame event.

        :param event: a Pygame event object from pygame.event.get()
        """
        # QUIT events (window close button) are usually handled in main.py,
        # but you *could* set flags here if you want the screen to react.
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p:
                # Toggle pause (but not during answer reveal or when duel hasn't started)
                if self.started and not self.winner and not self.reveal_answer_mode and not self.pass_penalty_mode:
                    self.paused = not self.paused

            elif event.key == pygame.K_x:
                # Pass function - 3 second penalty, show answer in red, stay with same player
                if self.started and not self.winner and not self.paused and not self.reveal_answer_mode and not self.pass_penalty_mode:
                    self.pass_penalty_mode = True
                    self.pass_penalty_timer_ms = 3000  # 3 seconds
                    # Parse answer from current image filename
                    current_filename = self.image_filenames[self.current_image_index]
                    self.current_answer = self._parse_answer_from_filename(current_filename)

            elif event.key == pygame.K_SPACE:
                if not self.started:
                    # At beginning of round, press SPACE to start.
                    self.started = True
                    self.current_image_index = (self.current_image_index + 1) % len(self.images)
                elif self.winner:
                    # If duel is over, press SPACE to return to FloorScreen.
                    self.request_screen_change = {
                        "screen": "floor",
                        "winner": self.winner,
                        "loser": self.loser,
                        "defender_category": self.defender_category
                    }
                elif not self.paused and not self.reveal_answer_mode:
                    # Enter answer reveal mode
                    self.reveal_answer_mode = True
                    self.reveal_timer_ms = 3000  # 3 seconds
                    # Parse answer from current image filename
                    current_filename = self.image_filenames[self.current_image_index]
                    self.current_answer = self._parse_answer_from_filename(current_filename)

            # You *could* also handle ESC here, but usually main.py handles quitting.

    def update(self, delta_ms):
        """
        Update the internal state of the duel.

        :param delta_ms: time elapsed since last frame, in milliseconds.
                         Typically from clock.tick().
        """
        # Handle pass penalty countdown
        if self.pass_penalty_mode:
            # Timer continues counting down (penalty)
            if self.remaining_ms[self.active_player] > 0:
                self.remaining_ms[self.active_player] = max(
                    0,
                    self.remaining_ms[self.active_player] - delta_ms
                )

            # Pass penalty timer counts down
            self.pass_penalty_timer_ms = max(0, self.pass_penalty_timer_ms - delta_ms)
            if self.pass_penalty_timer_ms == 0:
                # Penalty period is over, advance to next image but keep same player
                self.pass_penalty_mode = False
                self.current_image_index = (self.current_image_index + 1) % len(self.images)
                self.current_answer = ""
            return

        # Handle answer reveal countdown
        if self.reveal_answer_mode:
            self.reveal_timer_ms = max(0, self.reveal_timer_ms - delta_ms)
            if self.reveal_timer_ms == 0:
                # Reveal period is over, switch to next player
                self.reveal_answer_mode = False
                self.active_player = 2 if self.active_player == 1 else 1
                self.current_image_index = (self.current_image_index + 1) % len(self.images)
                self.current_answer = ""
            return

        # Only countdown timer if not paused and duel has started
        if self.started and not self.paused and self.remaining_ms[self.active_player] > 0:
            self.remaining_ms[self.active_player] = max(
                0,
                self.remaining_ms[self.active_player] - delta_ms
            )

        # Identify winner if any player's time reaches zero.
        if self.remaining_ms[self.active_player] == 0:
            self.winner = self.names_dict[3 - self.active_player]
            self.loser = self.names_dict[self.active_player]
            # Optionally, create and append the ending image.
            self.images.append(self._create_ending_image(self.winner))
            self.image_filenames.append(None)  # No filename for ending image
            self.current_image_index = len(self.images) - 1

    def draw(self):
        """
        Draw the entire duel view to the screen.
        """
        # Clear the screen with a background color.
        self.screen.fill((20, 20, 30))  # dark bluish-gray

        # -------------------------
        # Draw center image
        # -------------------------
        current_image = self.images[self.current_image_index]
        image_rect = current_image.get_rect(center=(self.width // 2, self.height // 2))
        # "blit" = copy one Surface onto another.
        self.screen.blit(current_image, image_rect)

        # -------------------------
        # Draw timers
        # -------------------------

        # Render timer text for each player.
        t1_text = self.font.render(
            self._format_time(self.remaining_ms[1]),
            True,
            (255, 255, 255)
        )
        t2_text = self.font.render(
            self._format_time(self.remaining_ms[2]),
            True,
            (255, 255, 255)
        )

        # Position player 1 timer at top-left.
        t1_rect = t1_text.get_rect(topleft=(20, 20))
        # Position player 2 timer at top-right, 20 px from right edge.
        t2_rect = t2_text.get_rect(topright=(self.width - 20, 20))

        # Highlight box behind active player's timer so it's visually clear.
        padding = 10
        if self.active_player == 1:
            highlight_rect = t1_rect.inflate(padding * 2, padding * 2)
        else:
            highlight_rect = t2_rect.inflate(padding * 2, padding * 2)

        # Draw filled rectangle for highlight.
        pygame.draw.rect(self.screen, (0, 150, 0), highlight_rect)

        # Draw timer texts.
        self.screen.blit(t1_text, t1_rect)
        self.screen.blit(t2_text, t2_rect)

        # -------------------------
        # Draw player names under timers
        # -------------------------
        if self.challenger_name:
            name1_text = self.name_font.render(
                self.challenger_name,
                True,
                (255, 255, 255)
            )
            name1_rect = name1_text.get_rect(topleft=(20, t1_rect.bottom + 15))
            self.screen.blit(name1_text, name1_rect)

        if self.defender_name:
            name2_text = self.name_font.render(
                self.defender_name,
                True,
                (255, 255, 255)
            )
            name2_rect = name2_text.get_rect(topright=(self.width - 20, t2_rect.bottom + 15))
            self.screen.blit(name2_text, name2_rect)

        # -------------------------
        # Draw category at top center
        # -------------------------
        if self.defender_category:
            category_text = self.name_font.render(
                self.defender_category,
                True,
                (255, 255, 255)
            )
            category_rect = category_text.get_rect(midtop=(self.width // 2, 20))
            self.screen.blit(category_text, category_rect)

        # -------------------------
        # Draw answer text if in reveal mode or pass penalty mode
        # -------------------------
        if (self.reveal_answer_mode or self.pass_penalty_mode) and self.current_answer:
            # Use red for pass penalty, yellow for normal reveal
            answer_color = (255, 0, 0) if self.pass_penalty_mode else (255, 255, 0)
            answer_text = self.answer_font.render(
                f"{self.current_answer}",
                True,
                answer_color
            )
            answer_rect = answer_text.get_rect(center=(self.width // 2, image_rect.bottom + 40))
            # Draw a semi-transparent background for better readability
            bg_rect = answer_rect.inflate(20, 10)
            bg_surface = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
            bg_surface.fill((0, 0, 0, 180))  # Black with alpha
            self.screen.blit(bg_surface, bg_rect)
            self.screen.blit(answer_text, answer_rect)

        # -------------------------
        # Draw PAUSED overlay
        # -------------------------
        if self.paused:
            pause_text = self.font.render("PAUSED", True, (255, 0, 0))
            pause_rect = pause_text.get_rect(center=(self.width // 2, self.height // 2))
            # Draw semi-transparent background
            bg_rect = pause_rect.inflate(40, 20)
            bg_surface = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
            bg_surface.fill((0, 0, 0, 200))  # Black with alpha
            self.screen.blit(bg_surface, bg_rect)
            self.screen.blit(pause_text, pause_rect)
