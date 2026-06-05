"""
evaluate.py
Static board evaluation for the minimax AI.

Returns a score in pawns (positive = good for White, negative = good for Black).
Covers:
  - Material balance
  - Piece-square tables (positional bonuses)
  - King safety (pawn shield, open files near king)
  - Pawn structure (doubled, isolated, passed pawns)
  - Super Pawn positional bonus (centralisation + mobility hint)
"""

from constants import PIECE_VALUES
from board     import coords, sq, on_board

# ── Piece-square tables (from White's perspective, rank 1 = index 0) ─────────

PST_PAWN = [
    [0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
    [0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05],
    [0.03, 0.03, 0.06, 0.08, 0.08, 0.06, 0.03, 0.03],
    [0.02, 0.02, 0.04, 0.10, 0.10, 0.04, 0.02, 0.02],
    [0.05, 0.05, 0.08, 0.12, 0.12, 0.08, 0.05, 0.05],
    [0.10, 0.10, 0.12, 0.15, 0.15, 0.12, 0.10, 0.10],
    [0.20, 0.20, 0.20, 0.20, 0.20, 0.20, 0.20, 0.20],
    [0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
]

PST_KNIGHT = [
    [-0.30,-0.20,-0.10,-0.10,-0.10,-0.10,-0.20,-0.30],
    [-0.20,-0.10, 0.00, 0.02, 0.02, 0.00,-0.10,-0.20],
    [-0.10, 0.02, 0.08, 0.10, 0.10, 0.08, 0.02,-0.10],
    [-0.10, 0.04, 0.10, 0.14, 0.14, 0.10, 0.04,-0.10],
    [-0.10, 0.04, 0.10, 0.14, 0.14, 0.10, 0.04,-0.10],
    [-0.10, 0.02, 0.08, 0.10, 0.10, 0.08, 0.02,-0.10],
    [-0.20,-0.10, 0.00, 0.02, 0.02, 0.00,-0.10,-0.20],
    [-0.30,-0.20,-0.10,-0.10,-0.10,-0.10,-0.20,-0.30],
]

PST_BISHOP = [
    [-0.10,-0.10,-0.10,-0.10,-0.10,-0.10,-0.10,-0.10],
    [-0.10, 0.04, 0.00, 0.00, 0.00, 0.00, 0.04,-0.10],
    [-0.10, 0.08, 0.08, 0.08, 0.08, 0.08, 0.08,-0.10],
    [-0.10, 0.00, 0.08, 0.12, 0.12, 0.08, 0.00,-0.10],
    [-0.10, 0.04, 0.08, 0.12, 0.12, 0.08, 0.04,-0.10],
    [-0.10, 0.06, 0.08, 0.06, 0.06, 0.08, 0.06,-0.10],
    [-0.10, 0.06, 0.00, 0.00, 0.00, 0.00, 0.06,-0.10],
    [-0.10,-0.10,-0.10,-0.10,-0.10,-0.10,-0.10,-0.10],
]

PST_ROOK = [
    [ 0.00, 0.00, 0.02, 0.04, 0.04, 0.02, 0.00, 0.00],
    [-0.02, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00,-0.02],
    [-0.02, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00,-0.02],
    [-0.02, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00,-0.02],
    [-0.02, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00,-0.02],
    [-0.02, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00,-0.02],
    [ 0.04, 0.06, 0.06, 0.06, 0.06, 0.06, 0.06, 0.04],
    [ 0.00, 0.00, 0.02, 0.04, 0.04, 0.02, 0.00, 0.00],
]

PST_QUEEN = [
    [-0.10,-0.04,-0.04,-0.02,-0.02,-0.04,-0.04,-0.10],
    [-0.04, 0.00, 0.02, 0.00, 0.00, 0.00, 0.00,-0.04],
    [-0.04, 0.02, 0.02, 0.02, 0.02, 0.02, 0.00,-0.04],
    [ 0.00, 0.00, 0.02, 0.02, 0.02, 0.02, 0.00,-0.02],
    [-0.02, 0.00, 0.02, 0.02, 0.02, 0.02, 0.00,-0.02],
    [-0.04, 0.00, 0.02, 0.02, 0.02, 0.02, 0.00,-0.04],
    [-0.04, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00,-0.04],
    [-0.10,-0.04,-0.04,-0.02,-0.02,-0.04,-0.04,-0.10],
]

PST_SUPER = [
    [-0.20,-0.10,-0.05,-0.05,-0.05,-0.05,-0.10,-0.20],
    [-0.10, 0.00, 0.04, 0.04, 0.04, 0.04, 0.00,-0.10],
    [-0.05, 0.04, 0.10, 0.12, 0.12, 0.10, 0.04,-0.05],
    [-0.05, 0.04, 0.12, 0.16, 0.16, 0.12, 0.04,-0.05],
    [-0.05, 0.04, 0.12, 0.16, 0.16, 0.12, 0.04,-0.05],
    [-0.05, 0.04, 0.10, 0.12, 0.12, 0.10, 0.04,-0.05],
    [-0.10, 0.00, 0.04, 0.04, 0.04, 0.04, 0.00,-0.10],
    [-0.20,-0.10,-0.05,-0.05,-0.05,-0.05,-0.10,-0.20],
]

PST_KING_MID = [
    [ 0.10, 0.14, 0.08,-0.02,-0.02, 0.08, 0.14, 0.10],
    [ 0.06, 0.06,-0.02,-0.06,-0.06,-0.02, 0.06, 0.06],
    [-0.04,-0.08,-0.10,-0.12,-0.12,-0.10,-0.08,-0.04],
    [-0.08,-0.12,-0.14,-0.16,-0.16,-0.14,-0.12,-0.08],
    [-0.10,-0.14,-0.16,-0.18,-0.18,-0.16,-0.14,-0.10],
    [-0.10,-0.14,-0.16,-0.18,-0.18,-0.16,-0.14,-0.10],
    [-0.08,-0.12,-0.14,-0.16,-0.16,-0.14,-0.12,-0.08],
    [-0.06,-0.08,-0.10,-0.12,-0.12,-0.10,-0.08,-0.06],
]

PST_KING_END = [
    [-0.20,-0.10,-0.10,-0.10,-0.10,-0.10,-0.10,-0.20],
    [-0.10, 0.00, 0.04, 0.06, 0.06, 0.04, 0.00,-0.10],
    [-0.10, 0.04, 0.08, 0.10, 0.10, 0.08, 0.04,-0.10],
    [-0.10, 0.06, 0.10, 0.12, 0.12, 0.10, 0.06,-0.10],
    [-0.10, 0.06, 0.10, 0.12, 0.12, 0.10, 0.06,-0.10],
    [-0.10, 0.04, 0.08, 0.10, 0.10, 0.08, 0.04,-0.10],
    [-0.10, 0.00, 0.04, 0.06, 0.06, 0.04, 0.00,-0.10],
    [-0.20,-0.10,-0.10,-0.10,-0.10,-0.10,-0.10,-0.20],
]

PST_MAP = {'P': PST_PAWN, 'N': PST_KNIGHT, 'B': PST_BISHOP,
           'R': PST_ROOK, 'Q': PST_QUEEN,  'S': PST_SUPER}


def _pst_value(kind, col, row, color, endgame=False):
    if kind == 'K':
        table = PST_KING_END if endgame else PST_KING_MID
    else:
        table = PST_MAP.get(kind)
        if table is None:
            return 0.0
    pst_row = row if color == 'w' else 7 - row
    return table[pst_row][col]


def _is_endgame(board):
    queens = sum(1 for p in board.grid.values() if p[1] == 'Q')
    majors = sum(1 for p in board.grid.values() if p[1] in ('Q', 'R'))
    return queens == 0 or majors <= 2


def _pawn_structure(board, color):
    score     = 0.0
    enemy     = 'b' if color == 'w' else 'w'
    pawn_cols = {}
    for square, piece in board.grid.items():
        if piece == color + 'P':
            c, r = coords(square)
            pawn_cols.setdefault(c, []).append(r)
    enemy_pawn_cols = set()
    for square, piece in board.grid.items():
        if piece == enemy + 'P':
            c, _ = coords(square)
            enemy_pawn_cols.add(c)
    for c, rows in pawn_cols.items():
        if len(rows) > 1:
            score -= 0.20 * (len(rows) - 1)
        if (c - 1) not in pawn_cols and (c + 1) not in pawn_cols:
            score -= 0.15
        if not any(ec in enemy_pawn_cols for ec in (c-1, c, c+1)):
            best = max(rows) if color == 'w' else min(rows)
            adv  = best if color == 'w' else 7 - best
            score += 0.10 + 0.08 * adv
    return score


def _king_safety(board, color):
    king_sq = board.find_king(color)
    if not king_sq:
        return 0.0
    kc, kr   = coords(king_sq)
    shield_r = kr + (1 if color == 'w' else -1)
    score    = 0.0
    if on_board(0, shield_r):
        for dc in (-1, 0, 1):
            tc = kc + dc
            if on_board(tc, shield_r) and board.piece_at(sq(tc, shield_r)) == color + 'P':
                score += 0.10
    return score


def evaluate(board) -> float:
    """Positive = good for White. Negative = good for Black."""
    from moves import is_checkmate, is_stalemate
    if is_checkmate(board, 'w'): return -9999.0
    if is_checkmate(board, 'b'): return  9999.0
    if is_stalemate(board, board.turn): return 0.0

    endgame = _is_endgame(board)
    score   = 0.0
    for square, piece in board.grid.items():
        color = piece[0]
        kind  = piece[1]
        c, r  = coords(square)
        sign  = 1.0 if color == 'w' else -1.0
        score += sign * PIECE_VALUES[kind]
        score += sign * _pst_value(kind, c, r, color, endgame)
    score += _pawn_structure(board, 'w') - _pawn_structure(board, 'b')
    if not endgame:
        score += _king_safety(board, 'w') - _king_safety(board, 'b')
    return score