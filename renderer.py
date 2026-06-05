"""
renderer.py
Handles all Pygame drawing: board squares, pieces, highlights, sidebar.
"""

import os
import pygame
from constants import *


# ── Asset loader ──────────────────────────────────────────────────────────────

def load_pieces(assets_dir: str) -> dict[str, pygame.Surface]:
    """
    Load piece images from assets/pieces/.
    Expected filenames: wK.png wQ.png wR.png wB.png wN.png wP.png wS.png
                        bK.png bQ.png bR.png bB.png bN.png bP.png bS.png
    Falls back to rendered text glyphs if a file is missing.
    """
    images = {}
    codes  = [c + t for c in ('w', 'b') for t in ('K', 'Q', 'R', 'B', 'N', 'P', 'S')]
    for code in codes:
        path = os.path.join(assets_dir, f"{code}.png")
        if os.path.exists(path):
            img = pygame.image.load(path).convert_alpha()
            images[code] = pygame.transform.smoothscale(img, (SQUARE_SIZE, SQUARE_SIZE))
        else:
            images[code] = _make_fallback_surface(code)
    return images


def _make_fallback_surface(code: str) -> pygame.Surface:
    """Generate a simple coloured text glyph when PNG is missing."""
    surf = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))

    is_white = code[0] == 'w'
    is_super = code[1] == 'S'

    # Circle background
    bg  = (255, 255, 255) if is_white else (40, 40, 40)
    rim = ACCENT_SUPER if is_super else ((180, 140, 60) if is_white else (100, 100, 120))
    cx = cy = SQUARE_SIZE // 2
    r  = SQUARE_SIZE // 2 - 4
    pygame.draw.circle(surf, rim, (cx, cy), r)
    pygame.draw.circle(surf, bg,  (cx, cy), r - 3)

    # Letter
    font_size  = 28 if is_super else 24
    font       = pygame.font.SysFont('segoeuisymbol', font_size, bold=True)
    symbol_map = {'K':'♔','Q':'♕','R':'♖','B':'♗','N':'♘','P':'♙','S':'★'}
    sym  = symbol_map.get(code[1], code[1])
    fg   = (30, 30, 30) if is_white else (220, 220, 220)
    if is_super:
        fg = ACCENT_SUPER if not is_white else (180, 80, 220)
    lbl  = font.render(sym, True, fg)
    rect = lbl.get_rect(center=(cx, cy))
    surf.blit(lbl, rect)
    return surf


# ── Renderer class ────────────────────────────────────────────────────────────

class Renderer:
    def __init__(self, screen: pygame.Surface, assets_dir: str):
        self.screen     = screen
        self.pieces     = load_pieces(assets_dir)

        # Pre-build semi-transparent overlay surfaces
        self._sel_surf   = self._alpha_rect(HIGHLIGHT_SEL)
        self._move_surf  = self._alpha_rect(HIGHLIGHT_MOVE)
        self._check_surf = self._alpha_rect(HIGHLIGHT_CHECK)
        self._last_from  = self._alpha_rect(LAST_MOVE_FROM)
        self._last_to    = self._alpha_rect(LAST_MOVE_TO)

        # Fonts
        self.font_title  = pygame.font.SysFont('georgia',      18, bold=True)
        self.font_label  = pygame.font.SysFont('georgia',      13)
        self.font_move   = pygame.font.SysFont('couriernew',   12)
        self.font_status = pygame.font.SysFont('georgia',      15, bold=True)
        self.font_coord  = pygame.font.SysFont('georgia',      11)

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _alpha_rect(rgba) -> pygame.Surface:
        s = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
        s.fill(rgba)
        return s

    def sq_to_pixel(self, col: int, row: int, flipped: bool = False):
        """
        Return top-left pixel (x, y) of a square.
        flipped=True when player plays Black (board drawn from Black's POV).
        """
        draw_col = 7 - col if flipped else col
        draw_row = row      if flipped else 7 - row
        x = BOARD_OFFSET_X + draw_col * SQUARE_SIZE
        y = BOARD_OFFSET_Y + draw_row * SQUARE_SIZE
        return x, y

    def pixel_to_sq(self, px: int, py: int, flipped: bool = False):
        """Return (col, row) from pixel, or None if outside board."""
        bx = px - BOARD_OFFSET_X
        by = py - BOARD_OFFSET_Y
        if not (0 <= bx < BOARD_SIZE and 0 <= by < BOARD_SIZE):
            return None
        draw_col = bx // SQUARE_SIZE
        draw_row = by // SQUARE_SIZE
        col = 7 - draw_col if flipped else draw_col
        row = draw_row      if flipped else 7 - draw_row
        return col, row

    # ── Background ────────────────────────────────────────────────────────────

    def draw_background(self):
        self.screen.fill(BG_DARK)

        # Sidebar card
        card = pygame.Rect(SIDEBAR_X - 8, BOARD_OFFSET_Y,
                           SIDEBAR_WIDTH + 8, BOARD_SIZE)
        pygame.draw.rect(self.screen, BG_SIDEBAR, card, border_radius=8)
        pygame.draw.rect(self.screen, BORDER_COLOR, card, 1, border_radius=8)

    # ── Board ─────────────────────────────────────────────────────────────────

    def draw_board(self, flipped: bool = False,
                   selected_sq: str | None = None,
                   legal_moves: list[str] | None = None,
                   king_check_sq: str | None = None,
                   last_move: tuple | None = None):
        from board import coords   # local import to avoid circular

        legal_moves = legal_moves or []

        for row in range(8):
            for col in range(8):
                x, y = self.sq_to_pixel(col, row, flipped)
                color = LIGHT_SQUARE if (col + row) % 2 == 0 else DARK_SQUARE
                pygame.draw.rect(self.screen, color,
                                 (x, y, SQUARE_SIZE, SQUARE_SIZE))

        # Last-move highlights
        if last_move:
            for lsq, surf in zip(last_move, [self._last_from, self._last_to]):
                c, r = coords(lsq)
                x, y = self.sq_to_pixel(c, r, flipped)
                self.screen.blit(surf, (x, y))

        # Check highlight
        if king_check_sq:
            c, r = coords(king_check_sq)
            x, y = self.sq_to_pixel(c, r, flipped)
            self.screen.blit(self._check_surf, (x, y))

        # Selected-square highlight
        if selected_sq:
            c, r = coords(selected_sq)
            x, y = self.sq_to_pixel(c, r, flipped)
            self.screen.blit(self._sel_surf, (x, y))

        # Legal-move dots
        for target in legal_moves:
            c, r = coords(target)
            x, y = self.sq_to_pixel(c, r, flipped)
            # Small circle in the centre
            cx = x + SQUARE_SIZE // 2
            cy = y + SQUARE_SIZE // 2
            dot_surf = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
            pygame.draw.circle(dot_surf, (20, 180, 20, 120),
                               (SQUARE_SIZE // 2, SQUARE_SIZE // 2), 10)
            self.screen.blit(dot_surf, (x, y))

        # Border around board
        pygame.draw.rect(self.screen, BORDER_COLOR,
                         (BOARD_OFFSET_X - 1, BOARD_OFFSET_Y - 1,
                          BOARD_SIZE + 2, BOARD_SIZE + 2), 2)

    # ── Coordinates ───────────────────────────────────────────────────────────

    def draw_coordinates(self, flipped: bool = False):
        files = 'abcdefgh'
        ranks = '12345678'

        for i in range(8):
            # File labels (a-h) below the board
            draw_col = 7 - i if flipped else i
            x = BOARD_OFFSET_X + draw_col * SQUARE_SIZE + SQUARE_SIZE // 2 - 4
            y = BOARD_OFFSET_Y + BOARD_SIZE + 4
            lbl = self.font_coord.render(files[i], True, TEXT_SECONDARY)
            self.screen.blit(lbl, (x, y))

            # Rank labels (1-8) left of the board
            draw_row = i if flipped else 7 - i
            y2 = BOARD_OFFSET_Y + draw_row * SQUARE_SIZE + SQUARE_SIZE // 2 - 6
            lbl2 = self.font_coord.render(ranks[i], True, TEXT_SECONDARY)
            self.screen.blit(lbl2, (BOARD_OFFSET_X - 16, y2))

    # ── Pieces ────────────────────────────────────────────────────────────────

    def draw_pieces(self, grid: dict, flipped: bool = False):
        from board import coords
        for square, piece in grid.items():
            c, r = coords(square)
            x, y = self.sq_to_pixel(c, r, flipped)
            if piece in self.pieces:
                self.screen.blit(self.pieces[piece], (x, y))

    # ── Sidebar ───────────────────────────────────────────────────────────────

    def draw_sidebar(self, turn: str, super_color: str,
                     player_color: str, player_side: str,
                     status_text: str, status_color,
                     move_log: list[str],
                     captured_w: list[str],
                     captured_b: list[str],
                     thinking: bool = False) -> dict:

        sx = SIDEBAR_X
        y  = BOARD_OFFSET_Y + 10

        # ── Title ──
        title = self.font_title.render("SUPER PAWN CHESS", True, ACCENT_GOLD)
        self.screen.blit(title, (sx, y))
        y += 26

        pygame.draw.line(self.screen, BORDER_COLOR,
                         (sx, y), (sx + SIDEBAR_WIDTH - 16, y))
        y += 10

        # ── Turn indicator ──
        turn_lbl = "White" if turn == 'w' else "Black"
        turn_col = (230, 230, 230) if turn == 'w' else (120, 120, 140)
        dot_col  = (255, 255, 255) if turn == 'w' else (60, 60, 80)
        pygame.draw.circle(self.screen, dot_col, (sx + 7, y + 7), 6)
        pygame.draw.circle(self.screen, BORDER_COLOR, (sx + 7, y + 7), 6, 1)
        t = self.font_label.render(f"Turn: {turn_lbl}", True, turn_col)
        self.screen.blit(t, (sx + 18, y + 1))
        y += 22

        # ── Side info ──
        your_side = "Super Pawn" if player_side == 'super' else "Normal"
        your_col  = "White" if player_color == 'w' else "Black"
        lbl1 = self.font_label.render(
            f"You: {your_col} ({your_side})", True, TEXT_SECONDARY)
        self.screen.blit(lbl1, (sx, y))
        y += 18

        ai_side  = "Normal" if player_side == 'super' else "Super Pawn"
        ai_col   = "Black" if player_color == 'w' else "White"
        lbl2 = self.font_label.render(
            f"AI:  {ai_col} ({ai_side})", True, TEXT_SECONDARY)
        self.screen.blit(lbl2, (sx, y))
        y += 22

        pygame.draw.line(self.screen, BORDER_COLOR,
                         (sx, y), (sx + SIDEBAR_WIDTH - 16, y))
        y += 8

        # ── Status ──
        if thinking:
            status_text  = "AI is thinking..."
            status_color = STATUS_THINKING
        s = self.font_status.render(status_text, True, status_color)
        self.screen.blit(s, (sx, y))
        y += 24

        pygame.draw.line(self.screen, BORDER_COLOR,
                         (sx, y), (sx + SIDEBAR_WIDTH - 16, y))
        y += 8

        # ── Captured pieces ──
        cap_lbl = self.font_label.render("Captured:", True, TEXT_SECONDARY)
        self.screen.blit(cap_lbl, (sx, y))
        y += 16

        # White's captures (pieces Black lost)
        self._draw_captured_row(captured_w, sx, y, scale=20)
        y += 24
        self._draw_captured_row(captured_b, sx, y, scale=20)
        y += 28

        pygame.draw.line(self.screen, BORDER_COLOR,
                         (sx, y), (sx + SIDEBAR_WIDTH - 16, y))
        y += 8

        # ── Resign button ──
        resign_rect = pygame.Rect(sx, y, SIDEBAR_WIDTH - 16, 32)
        pygame.draw.rect(self.screen, (200, 80, 80), resign_rect, border_radius=6)
        pygame.draw.rect(self.screen, BORDER_COLOR, resign_rect, 1, border_radius=6)
        resign_lbl = self.font_label.render("Resign", True, TEXT_DARK)
        self.screen.blit(resign_lbl, resign_lbl.get_rect(center=resign_rect.center))
        y += 40

        pygame.draw.line(self.screen, BORDER_COLOR,
                         (sx, y), (sx + SIDEBAR_WIDTH - 16, y))
        y += 8

        # ── Move log ──
        ml_lbl = self.font_label.render("Move Log:", True, TEXT_SECONDARY)
        self.screen.blit(ml_lbl, (sx, y))
        y += 16

        max_lines = (BOARD_OFFSET_Y + BOARD_SIZE - y) // 14
        visible   = move_log[-max_lines:] if len(move_log) > max_lines else move_log
        for entry in visible:
            line = self.font_move.render(entry, True, TEXT_PRIMARY)
            self.screen.blit(line, (sx, y))
            y += 14

        return {'resign': resign_rect}

    def _draw_captured_row(self, pieces: list[str], x: int, y: int, scale: int = 20):
        for i, p in enumerate(pieces):
            if p in self.pieces:
                small = pygame.transform.smoothscale(self.pieces[p], (scale, scale))
                self.screen.blit(small, (x + i * (scale + 1), y))

    # ── Promotion dialog ─────────────────────────────────────────────────────

    def draw_promotion_dialog(self, color: str):
        """Draws a centred overlay asking the player to choose a promotion piece."""
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        choices  = ['Q', 'R', 'B', 'N']
        box_w    = 60
        total_w  = len(choices) * (box_w + 8) + 8
        bx       = (WINDOW_WIDTH  - total_w) // 2
        by       = (WINDOW_HEIGHT - box_w - 40) // 2

        # Title
        t = self.font_title.render("Choose Promotion", True, ACCENT_GOLD)
        self.screen.blit(t, (bx, by - 28))

        rects = {}
        for i, kind in enumerate(choices):
            rx = bx + i * (box_w + 8) + 8
            ry = by
            rect = pygame.Rect(rx, ry, box_w, box_w)
            pygame.draw.rect(self.screen, BG_CARD, rect, border_radius=8)
            pygame.draw.rect(self.screen, ACCENT_GOLD, rect, 2, border_radius=8)

            code = color + kind
            if code in self.pieces:
                img = pygame.transform.smoothscale(self.pieces[code], (52, 52))
                self.screen.blit(img, (rx + 4, ry + 4))
            rects[kind] = rect

        return rects

    # ── Game-Over overlay ─────────────────────────────────────────────────────

    def draw_game_over(self, message: str):
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        font_big = pygame.font.SysFont('georgia', 36, bold=True)
        font_sub = pygame.font.SysFont('georgia', 18)

        t1 = font_big.render(message, True, ACCENT_GOLD)
        t2 = font_sub.render("Press R to restart", True, TEXT_SECONDARY)

        self.screen.blit(t1, t1.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 20)))
        self.screen.blit(t2, t2.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 20)))

    # ── Start screen ──────────────────────────────────────────────────────────

    def draw_start_screen(self,
                          hover_color: str | None,
                          hover_side:  str | None,
                          sel_color:   str | None,
                          sel_side:    str | None) -> dict:
        """
        Draw the start/selection screen.
        Returns a dict of clickable Rects:
          {'white': Rect, 'black': Rect, 'super': Rect, 'normal': Rect, 'start': Rect}
        """
        self.screen.fill(BG_DARK)

        # Title
        font_hero = pygame.font.SysFont('georgia', 38, bold=True)
        font_sub  = pygame.font.SysFont('georgia', 14)
        t = font_hero.render("SUPER PAWN CHESS", True, ACCENT_GOLD)
        self.screen.blit(t, t.get_rect(center=(WINDOW_WIDTH // 2, 80)))
        st = font_sub.render("One king, one queen, one super pawn — against the full army", True, TEXT_SECONDARY)
        self.screen.blit(st, st.get_rect(center=(WINDOW_WIDTH // 2, 118)))

        rects = {}

        # ── Choose colour ──
        lbl = self.font_title.render("Choose your colour:", True, TEXT_PRIMARY)
        self.screen.blit(lbl, lbl.get_rect(center=(WINDOW_WIDTH // 2, 168)))

        for i, (ckey, clabel) in enumerate([('w', 'White'), ('b', 'Black')]):
            rx = WINDOW_WIDTH // 2 - 130 + i * 140
            ry = 185
            rect = pygame.Rect(rx, ry, 120, 44)
            rects[ckey] = rect
            active  = sel_color == ckey
            hovered = hover_color == ckey
            bg      = ACCENT_GOLD if active else (BG_CARD if not hovered else (65, 65, 78))
            fg      = TEXT_DARK if active else TEXT_PRIMARY
            pygame.draw.rect(self.screen, bg, rect, border_radius=8)
            if active:
                pygame.draw.rect(self.screen, WHITE_COLOR, rect, 2, border_radius=8)
            ct = self.font_title.render(clabel, True, fg)
            self.screen.blit(ct, ct.get_rect(center=rect.center))

        # ── Choose side ──
        lbl2 = self.font_title.render("Choose your side:", True, TEXT_PRIMARY)
        self.screen.blit(lbl2, lbl2.get_rect(center=(WINDOW_WIDTH // 2, 260)))

        side_info = [
            ('super',  'Super Pawn',  'King · Queen · Super Pawn · 8 Pawns'),
            ('normal', 'Normal',      'King · Queen · 2 Rooks · 2 Bishops · 2 Knights · 8 Pawns'),
        ]
        for i, (skey, stitle, sdesc) in enumerate(side_info):
            rx = WINDOW_WIDTH // 2 - 230 + i * 250
            ry = 278
            rect = pygame.Rect(rx, ry, 210, 66)
            rects[skey] = rect
            active  = sel_side == skey
            hovered = hover_side == skey
            bg = ACCENT_SUPER if (active and skey == 'super') else \
                 (ACCENT_GOLD  if (active and skey == 'normal') else
                 (BG_CARD if not hovered else (65, 65, 78)))
            fg = TEXT_DARK if active else TEXT_PRIMARY
            pygame.draw.rect(self.screen, bg, rect, border_radius=10)
            if active:
                pygame.draw.rect(self.screen, WHITE_COLOR, rect, 2, border_radius=10)
            st2 = self.font_title.render(stitle, True, fg)
            sd2 = self.font_coord.render(sdesc, True, fg if active else TEXT_SECONDARY)
            self.screen.blit(st2, st2.get_rect(center=(rect.centerx, rect.y + 22)))
            self.screen.blit(sd2, sd2.get_rect(center=(rect.centerx, rect.y + 44)))

        # ── Start button ──
        can_start = sel_color is not None and sel_side is not None
        start_rect = pygame.Rect(WINDOW_WIDTH // 2 - 80, 380, 160, 48)
        rects['start'] = start_rect
        sbg = ACCENT_GOLD if can_start else BORDER_COLOR
        sfg = TEXT_DARK   if can_start else TEXT_SECONDARY
        pygame.draw.rect(self.screen, sbg, start_rect, border_radius=10)
        sl  = self.font_title.render("START GAME", True, sfg)
        self.screen.blit(sl, sl.get_rect(center=start_rect.center))

        # Super Pawn description box
        info_y = 450
        desc_lines = [
            "★ The Super Pawn combines the power of a Queen and a Knight.",
            "  It slides in all 8 directions AND can jump like a Knight.",
            "  The Super Pawn side has no Rooks, Bishops, or Knights — and cannot castle.",
        ]
        for dl in desc_lines:
            dl_surf = self.font_coord.render(dl, True, TEXT_SECONDARY)
            self.screen.blit(dl_surf, dl_surf.get_rect(center=(WINDOW_WIDTH // 2, info_y)))
            info_y += 16

        return rects