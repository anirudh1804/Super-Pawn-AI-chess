"""
board.py
Manages the 8×8 grid, piece placement, and coordinate utilities.
Board is stored as a dict: algebraic_square -> piece_code  e.g. 'e1' -> 'wK'
"""

from constants import (
    NORMAL_WHITE_BACK, NORMAL_BLACK_BACK,
    SUPER_WHITE_BACK,  SUPER_BLACK_BACK,
    NORMAL_WHITE_PAWNS, NORMAL_BLACK_PAWNS,
    SUPER_WHITE_PAWNS,  SUPER_BLACK_PAWNS,
)


# ── Coordinate helpers ────────────────────────────────────────────────────────

def sq(col: int, row: int) -> str:
    """(col, row) → algebraic  e.g. (0,0) → 'a1'  (col 0-7, row 0-7, row 0 = rank 1)"""
    return chr(ord('a') + col) + str(row + 1)


def coords(square: str):
    """algebraic → (col, row)  e.g. 'a1' → (0, 0)"""
    return ord(square[0]) - ord('a'), int(square[1]) - 1


def on_board(col: int, row: int) -> bool:
    return 0 <= col <= 7 and 0 <= row <= 7


def square_color(col: int, row: int) -> str:
    """Returns 'light' or 'dark'."""
    return 'light' if (col + row) % 2 == 0 else 'dark'


# ── Board class ───────────────────────────────────────────────────────────────

class Board:
    """
    Attributes
    ----------
    grid          : dict[str, str]  algebraic → piece_code ('wK', 'bP', 'wS' …)
    turn          : 'w' or 'b'
    super_color   : 'w' or 'b'  — which side has the Super-Pawn pieces
    castling      : dict  {'wK': bool, 'wQ': bool, 'bK': bool, 'bQ': bool}
                    (only relevant for the normal side; super side can never castle)
    en_passant    : str | None  — square behind a double-pushed pawn
    half_moves    : int  (50-move rule counter)
    full_moves    : int
    last_move     : tuple | None  (from_sq, to_sq)
    """

    def __init__(self, player_color: str = 'w', player_side: str = 'super'):
        """
        player_color : 'w' or 'b'   — the human's piece colour
        player_side  : 'super' or 'normal'
        The AI always gets the opposite side/colour.
        """
        self.player_color = player_color
        self.player_side  = player_side

        # Determine which colour plays the super-pawn pieces
        if player_side == 'super':
            self.super_color = player_color
        else:
            self.super_color = 'b' if player_color == 'w' else 'w'

        self.grid       : dict[str, str]  = {}
        self.turn       : str             = 'w'          # White always moves first
        self.castling   : dict[str, bool] = {'wK': True, 'wQ': True,
                                              'bK': True, 'bQ': True}
        self.en_passant : str | None      = None
        self.half_moves : int             = 0
        self.full_moves : int             = 1
        self.last_move  : tuple | None    = None         # (from_sq, to_sq)

        self._setup()

    # ── Setup ─────────────────────────────────────────────────────────────────

    def _setup(self):
        """Place all pieces according to super_color."""
        sc = self.super_color
        nc = 'b' if sc == 'w' else 'w'   # normal colour

        # --- Super-Pawn side ---
        if sc == 'w':
            self.grid.update(SUPER_WHITE_BACK)
            self.grid.update(SUPER_WHITE_PAWNS)
            # Super side has no rooks → no castling rights
            self.castling['wK'] = False
            self.castling['wQ'] = False
        else:
            self.grid.update(SUPER_BLACK_BACK)
            self.grid.update(SUPER_BLACK_PAWNS)
            self.castling['bK'] = False
            self.castling['bQ'] = False

        # --- Normal side ---
        if nc == 'w':
            self.grid.update(NORMAL_WHITE_BACK)
            self.grid.update(NORMAL_WHITE_PAWNS)
        else:
            self.grid.update(NORMAL_BLACK_BACK)
            self.grid.update(NORMAL_BLACK_PAWNS)

    # ── Queries ───────────────────────────────────────────────────────────────

    def piece_at(self, square: str) -> str | None:
        return self.grid.get(square)

    def color_at(self, square: str) -> str | None:
        p = self.grid.get(square)
        return p[0] if p else None

    def is_empty(self, square: str) -> bool:
        return square not in self.grid

    def find_king(self, color: str) -> str | None:
        for sq_name, pc in self.grid.items():
            if pc == color + 'K':
                return sq_name
        return None

    def pieces_of(self, color: str) -> dict[str, str]:
        """Return {square: piece} for all pieces of given colour."""
        return {s: p for s, p in self.grid.items() if p[0] == color}

    # ── Move execution (raw — no legality check here) ─────────────────────────

    def apply_move(self, from_sq: str, to_sq: str,
                   promotion: str | None = None) -> dict:
        """
        Execute a move and return an undo record.
        Handles: normal moves, captures, en-passant, castling, promotion.
        """
        piece      = self.grid[from_sq]
        color      = piece[0]
        kind       = piece[1]
        captured   = self.grid.get(to_sq)
        prev_ep    = self.en_passant
        prev_cast  = dict(self.castling)
        prev_half  = self.half_moves
        ep_capture = None       # square of en-passant captured pawn

        # -- Move piece --
        del self.grid[from_sq]
        self.grid[to_sq] = piece

        # -- Promotion --
        if kind == 'P' and (to_sq[1] == '8' or to_sq[1] == '1'):
            promo_piece = promotion if promotion else 'Q'
            self.grid[to_sq] = color + promo_piece

        # -- En passant capture --
        if kind == 'P' and to_sq == self.en_passant:
            ep_row = '5' if color == 'w' else '4'
            ep_capture = to_sq[0] + ep_row
            captured = self.grid.pop(ep_capture, None)

        # -- Set new en-passant square --
        self.en_passant = None
        if kind == 'P':
            fc, fr = coords(from_sq)
            tc, tr = coords(to_sq)
            if abs(tr - fr) == 2:
                ep_col = tc
                ep_row = (fr + tr) // 2
                self.en_passant = sq(ep_col, ep_row)

        # -- Castling move --
        if kind == 'K':
            fc, fr = coords(from_sq)
            tc, tr = coords(to_sq)
            if abs(tc - fc) == 2:
                # King-side
                if tc > fc:
                    rook_from = sq(7, fr)
                    rook_to   = sq(5, fr)
                # Queen-side
                else:
                    rook_from = sq(0, fr)
                    rook_to   = sq(3, fr)
                rook = self.grid.pop(rook_from)
                self.grid[rook_to] = rook

        # -- Update castling rights --
        if kind == 'K':
            self.castling[color + 'K'] = False
            self.castling[color + 'Q'] = False
        if kind == 'R':
            fc, _ = coords(from_sq)
            if fc == 0: self.castling[color + 'Q'] = False
            if fc == 7: self.castling[color + 'K'] = False

        # -- Half-move clock --
        if kind == 'P' or captured:
            self.half_moves = 0
        else:
            self.half_moves += 1

        # -- Full-move counter --
        if color == 'b':
            self.full_moves += 1

        # -- Flip turn --
        self.turn = 'b' if color == 'w' else 'w'
        self.last_move = (from_sq, to_sq)

        return {
            'from_sq'   : from_sq,
            'to_sq'     : to_sq,
            'piece'     : piece,
            'captured'  : captured,
            'ep_capture': ep_capture,
            'ep_sq'     : prev_ep,
            'castling'  : prev_cast,
            'half_moves': prev_half,
            'last_move' : self.last_move,
            'promotion' : promotion,
        }

    def undo_move(self, record: dict):
        """Restore board to state before apply_move was called."""
        from_sq    = record['from_sq']
        to_sq      = record['to_sq']
        piece      = record['piece']
        captured   = record['captured']
        ep_capture = record['ep_capture']
        color      = piece[0]

        # Restore moved piece (handles promotion too)
        self.grid[from_sq] = piece
        if to_sq in self.grid:
            del self.grid[to_sq]

        # Restore capture
        if captured:
            restore_sq = ep_capture if ep_capture else to_sq
            self.grid[restore_sq] = captured

        # Undo castling rook move
        if piece[1] == 'K':
            fc, fr = coords(from_sq)
            tc, _  = coords(to_sq)
            if abs(tc - fc) == 2:
                if tc > fc:
                    self.grid[sq(7, fr)] = color + 'R'
                    if sq(5, fr) in self.grid: del self.grid[sq(5, fr)]
                else:
                    self.grid[sq(0, fr)] = color + 'R'
                    if sq(3, fr) in self.grid: del self.grid[sq(3, fr)]

        # Restore state
        self.en_passant = record['ep_sq']
        self.castling   = record['castling']
        self.half_moves = record['half_moves']
        if color == 'b':
            self.full_moves -= 1
        self.turn      = color
        self.last_move = record['last_move']

    # ── Debug ─────────────────────────────────────────────────────────────────

    def print_board(self):
        """ASCII dump for debugging."""
        print("  a  b  c  d  e  f  g  h")
        for row in range(7, -1, -1):
            line = f"{row+1} "
            for col in range(8):
                p = self.grid.get(sq(col, row), '..')
                line += f"{p:<3}"
            print(line)
        print(f"Turn: {self.turn}  EP: {self.en_passant}  "
              f"Castling: {self.castling}")