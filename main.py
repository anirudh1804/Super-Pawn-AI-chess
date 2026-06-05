"""
main.py
Entry point. Full game loop: START → PLAYING → PROMOTION → GAME_OVER.
Phase 3: AI wired in via background thread with "thinking" indicator.
"""

import sys, os, threading
import pygame

from constants import *
from board     import Board, sq as to_alg
from renderer  import Renderer
from moves     import (get_legal_moves, get_all_legal_moves,
                       is_in_check, is_checkmate, is_stalemate,
                       is_insufficient_material, move_to_notation)
from ai        import get_best_move

# Custom event posted when AI finishes thinking
AI_MOVE_EVENT = pygame.USEREVENT + 1


# ── GameState ─────────────────────────────────────────────────────────────────

class GameState:
    def __init__(self):
        self.reset()

    def reset(self):
        self.board            = None
        self.flipped          = False
        self.selected_sq      = None
        self.legal_move_map   = {}
        self.promo_from       = None
        self.promo_to         = None
        self.promo_color      = None
        self.promo_rects      = {}
        self.sidebar_rects    = {}   # resign button rect
        self.move_log         = []
        self.captured_w       = []
        self.captured_b       = []
        self.status_text      = "Your turn"
        self.status_color     = STATUS_NORMAL
        self.thinking         = False
        self.game_over_msg    = ""
        self.king_check_sq    = None
        self.pending_ai_move  = None   # set by AI thread

    def start_game(self, player_color, player_side):
        self.reset()
        self.board   = Board(player_color=player_color, player_side=player_side)
        self.flipped = (player_color == 'b')
        self._refresh_status()

    # ── Status ────────────────────────────────────────────────────────────────

    def _refresh_status(self):
        color = self.board.turn
        self.king_check_sq = None

        if is_checkmate(self.board, color):
            winner = "Black" if color == 'w' else "White"
            self.status_text   = f"Checkmate — {winner} wins!"
            self.status_color  = STATUS_MATE
            self.game_over_msg = f"{winner} wins by Checkmate!"
            return 'checkmate'

        if is_stalemate(self.board, color):
            self.status_text   = "Stalemate — Draw!"
            self.status_color  = STATUS_CHECK
            self.game_over_msg = "Stalemate — It's a Draw!"
            return 'stalemate'

        if is_insufficient_material(self.board):
            self.status_text   = "Insufficient material — Draw!"
            self.status_color  = STATUS_CHECK
            self.game_over_msg = "Draw — Insufficient Material"
            return 'draw'

        if is_in_check(self.board, color):
            self.king_check_sq = self.board.find_king(color)
            self.status_text   = "Check!"
            self.status_color  = STATUS_CHECK
            return 'check'

        is_player = (color == self.board.player_color)
        self.status_text  = "Your turn" if is_player else "AI thinking..."
        self.status_color = STATUS_NORMAL
        return 'normal'

    # ── Player click ──────────────────────────────────────────────────────────

    def handle_click(self, clicked_sq):
        board = self.board
        color = board.player_color
        if board.turn != color:
            return None

        piece_at = board.piece_at(clicked_sq)

        if self.selected_sq:
            if clicked_sq in self.legal_move_map:
                from_sq, to_sq, flag = self.legal_move_map[clicked_sq]
                if flag and flag.startswith('promo_'):
                    self.promo_from  = from_sq
                    self.promo_to    = to_sq
                    self.promo_color = color
                    self.selected_sq = None
                    self.legal_move_map = {}
                    return 'needs_promo'
                self._execute_move(from_sq, to_sq, flag)
                self.selected_sq    = None
                self.legal_move_map = {}
                result = self._refresh_status()
                return 'game_over' if result in ('checkmate','stalemate','draw') else 'moved'
            elif piece_at and piece_at[0] == color:
                self._select(clicked_sq)
                return None
            else:
                self.selected_sq    = None
                self.legal_move_map = {}
                return None

        if piece_at and piece_at[0] == color:
            self._select(clicked_sq)
        return None

    def _select(self, square):
        self.selected_sq  = square
        moves = get_legal_moves(self.board, square)
        self.legal_move_map = {}
        for m in moves:
            _, to_sq, _ = m
            if to_sq not in self.legal_move_map:
                self.legal_move_map[to_sq] = m

    def handle_promotion_choice(self, piece_kind):
        flag = 'promo_' + piece_kind
        self._execute_move(self.promo_from, self.promo_to, flag)
        self.promo_from = self.promo_to = self.promo_color = None
        self.promo_rects = {}
        result = self._refresh_status()
        return 'game_over' if result in ('checkmate','stalemate','draw') else 'moved'

    # ── AI move apply (called from main thread after thread posts event) ───────

    def apply_ai_move(self):
        move = self.pending_ai_move
        self.pending_ai_move = None
        self.thinking        = False
        if move is None:
            return 'game_over'
        from_sq, to_sq, flag = move
        self._execute_move(from_sq, to_sq, flag)
        result = self._refresh_status()
        return 'game_over' if result in ('checkmate','stalemate','draw') else None

    # ── Execute move ──────────────────────────────────────────────────────────

    def _execute_move(self, from_sq, to_sq, flag):
        board  = self.board
        piece  = board.piece_at(from_sq)
        color  = piece[0]
        notation = move_to_notation(board, from_sq, to_sq, flag)

        captured = board.piece_at(to_sq)
        if flag == 'ep':
            ep_row   = '5' if color == 'w' else '4'
            captured = board.piece_at(to_sq[0] + ep_row)

        promo = flag[-1] if flag and flag.startswith('promo_') else None
        board.apply_move(from_sq, to_sq, promotion=promo)

        if captured:
            (self.captured_w if color == 'w' else self.captured_b).append(captured)

        if color == 'w':
            self.move_log.append(f"{board.full_moves - 1}. {notation}")
        else:
            if self.move_log:
                self.move_log[-1] += f"  {notation}"
            else:
                self.move_log.append(f"... {notation}")


# ── AI thread launcher ────────────────────────────────────────────────────────

def launch_ai_thread(gs):
    """Run AI search in background; post AI_MOVE_EVENT when done."""
    ai_color = 'b' if gs.board.player_color == 'w' else 'w'

    def worker():
        move = get_best_move(gs.board, AI_DEPTH, ai_color)
        gs.pending_ai_move = move
        pygame.event.post(pygame.event.Event(AI_MOVE_EVENT))

    t = threading.Thread(target=worker, daemon=True)
    t.start()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    pygame.init()
    pygame.display.set_caption("Super Pawn Chess")
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    clock  = pygame.time.Clock()

    assets_dir = os.path.join(os.path.dirname(__file__), 'assets', 'pieces')
    renderer   = Renderer(screen, assets_dir)

    state       = STATE_START
    gs          = GameState()
    sel_color   = None
    sel_side    = None
    hover_color = None
    hover_side  = None
    start_rects = {}

    while True:
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # ── AI move ready ─────────────────────────────────────────────────
            if event.type == AI_MOVE_EVENT and state == STATE_PLAYING:
                result = gs.apply_ai_move()
                if result == 'game_over':
                    state = STATE_GAME_OVER

            # ── START SCREEN ──────────────────────────────────────────────────
            elif state == STATE_START:
                if event.type == pygame.MOUSEMOTION:
                    hover_color = hover_side = None
                    for key, rect in start_rects.items():
                        if rect.collidepoint(mouse_pos):
                            if key in ('w','b'):             hover_color = key
                            elif key in ('super','normal'):  hover_side  = key

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for key, rect in start_rects.items():
                        if rect.collidepoint(mouse_pos):
                            if key in ('w','b'):
                                sel_color = key
                            elif key in ('super','normal'):
                                sel_side = key
                            elif key == 'start' and sel_color and sel_side:
                                gs.start_game(sel_color, sel_side)
                                state = STATE_PLAYING
                                # If AI moves first (player is Black)
                                if gs.board.turn != gs.board.player_color:
                                    gs.thinking = True
                                    launch_ai_thread(gs)

            # ── PROMOTION ─────────────────────────────────────────────────────
            elif state == STATE_PROMOTION:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for kind, rect in gs.promo_rects.items():
                        if rect.collidepoint(mouse_pos):
                            result = gs.handle_promotion_choice(kind)
                            if result == 'game_over':
                                state = STATE_GAME_OVER
                            else:
                                state = STATE_PLAYING
                                # Trigger AI after promotion
                                if gs.board.turn != gs.board.player_color:
                                    gs.thinking = True
                                    launch_ai_thread(gs)

            # ── PLAYING ───────────────────────────────────────────────────────
            elif state == STATE_PLAYING:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                    state = STATE_START
                    sel_color = sel_side = None

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # Check resign button first
                    if 'resign' in gs.sidebar_rects and gs.sidebar_rects['resign'].collidepoint(mouse_pos):
                        opponent = "AI" if gs.board.turn != gs.board.player_color else "You"
                        winner = "AI wins" if gs.board.turn == gs.board.player_color else "You win"
                        gs.game_over_msg = f"{winner} — opponent resigned"
                        state = STATE_GAME_OVER
                    elif gs.thinking:
                        pass   # ignore clicks while AI is thinking
                    else:
                        hit = renderer.pixel_to_sq(*mouse_pos, gs.flipped)
                        if hit:
                            clicked_sq = to_alg(*hit)
                            result = gs.handle_click(clicked_sq)
                            if result == 'needs_promo':
                                state = STATE_PROMOTION
                            elif result == 'game_over':
                                state = STATE_GAME_OVER
                            elif result == 'moved':
                                # Player moved — trigger AI
                                if gs.board.turn != gs.board.player_color:
                                    gs.thinking = True
                                    launch_ai_thread(gs)

            # ── GAME OVER ─────────────────────────────────────────────────────
            elif state == STATE_GAME_OVER:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                    state = STATE_START
                    sel_color = sel_side = None

        # ── Draw ──────────────────────────────────────────────────────────────
        if state == STATE_START:
            start_rects = renderer.draw_start_screen(
                hover_color, hover_side, sel_color, sel_side)

        elif state in (STATE_PLAYING, STATE_PROMOTION, STATE_GAME_OVER):
            board = gs.board
            renderer.draw_background()
            renderer.draw_board(
                flipped       = gs.flipped,
                selected_sq   = gs.selected_sq,
                legal_moves   = list(gs.legal_move_map.keys()),
                king_check_sq = gs.king_check_sq,
                last_move     = board.last_move,
            )
            renderer.draw_coordinates(gs.flipped)
            renderer.draw_pieces(board.grid, gs.flipped)
            gs.sidebar_rects = renderer.draw_sidebar(
                turn         = board.turn,
                super_color  = board.super_color,
                player_color = board.player_color,
                player_side  = board.player_side,
                status_text  = gs.status_text,
                status_color = gs.status_color,
                move_log     = gs.move_log,
                captured_w   = gs.captured_w,
                captured_b   = gs.captured_b,
                thinking     = gs.thinking,
            )
            if state == STATE_PROMOTION:
                gs.promo_rects = renderer.draw_promotion_dialog(gs.promo_color)
            if state == STATE_GAME_OVER:
                renderer.draw_game_over(gs.game_over_msg)

        pygame.display.flip()
        clock.tick(FPS)


if __name__ == '__main__':
    main()