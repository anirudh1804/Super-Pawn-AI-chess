"""
moves.py
Complete move generation for Super Pawn Chess.

Public API
----------
get_pseudo_moves(board, square)         -> list[tuple]
get_legal_moves(board, square)          -> list[tuple]
get_all_legal_moves(board, color)       -> list[tuple]
is_in_check(board, color)               -> bool
is_checkmate(board, color)              -> bool
is_stalemate(board, color)              -> bool
is_insufficient_material(board)         -> bool

Each move is a tuple:
  (from_sq, to_sq, flag)

flag values
-----------
  None          normal move / capture
  'ep'          en-passant capture
  'castle_k'    king-side castling
  'castle_q'    queen-side castling
  'promo_Q'     pawn promotion → Queen
  'promo_R'     pawn promotion → Rook
  'promo_B'     pawn promotion → Bishop
  'promo_N'     pawn promotion → Knight
"""

from board import sq, coords, on_board
from constants import (
    QUEEN_DIRS, ROOK_DIRS, BISHOP_DIRS, KNIGHT_MOVES,
)


# ── Piece-specific pseudo-move generators ─────────────────────────────────────

def _pawn_moves(board, square: str, color: str) -> list[tuple]:
    moves = []
    col, row = coords(square)
    direction = 1 if color == 'w' else -1
    start_row = 1   if color == 'w' else 6
    promo_row = 7   if color == 'w' else 0
    flags     = ['promo_Q', 'promo_R', 'promo_B', 'promo_N']

    # Helper to add (with or without promotion)
    def add(to_col, to_row, flag=None):
        if not on_board(to_col, to_row):
            return
        target = sq(to_col, to_row)
        if to_row == promo_row:
            for pf in flags:
                moves.append((square, target, pf))
        else:
            moves.append((square, target, flag))

    # Single push
    fc, fr = col, row + direction
    if on_board(fc, fr) and board.is_empty(sq(fc, fr)):
        add(fc, fr)
        # Double push from starting rank
        if row == start_row:
            fc2, fr2 = col, row + 2 * direction
            if on_board(fc2, fr2) and board.is_empty(sq(fc2, fr2)):
                add(fc2, fr2)

    # Diagonal captures
    for dc in (-1, 1):
        tc, tr = col + dc, row + direction
        if not on_board(tc, tr):
            continue
        target = sq(tc, tr)
        # Normal capture
        if board.color_at(target) not in (None, color):
            add(tc, tr)
        # En passant
        elif target == board.en_passant:
            moves.append((square, target, 'ep'))

    return moves


def _knight_moves(board, square: str, color: str) -> list[tuple]:
    moves = []
    col, row = coords(square)
    for dc, dr in KNIGHT_MOVES:
        tc, tr = col + dc, row + dr
        if not on_board(tc, tr):
            continue
        target = sq(tc, tr)
        if board.color_at(target) != color:   # empty or enemy
            moves.append((square, target, None))
    return moves


def _sliding_moves(board, square: str, color: str,
                   directions: list) -> list[tuple]:
    moves = []
    col, row = coords(square)
    for dc, dr in directions:
        tc, tr = col + dc, row + dr
        while on_board(tc, tr):
            target  = sq(tc, tr)
            occ_col = board.color_at(target)
            if occ_col is None:
                moves.append((square, target, None))
            elif occ_col != color:
                moves.append((square, target, None))   # capture
                break
            else:
                break   # blocked by own piece
            tc += dc
            tr += dr
    return moves


def _king_moves(board, square: str, color: str) -> list[tuple]:
    moves = []
    col, row = coords(square)

    # Normal one-square moves
    for dc, dr in QUEEN_DIRS:
        tc, tr = col + dc, row + dr
        if not on_board(tc, tr):
            continue
        target = sq(tc, tr)
        if board.color_at(target) != color:
            moves.append((square, target, None))

    # Castling — only available if rights exist
    back_row = 0 if color == 'w' else 7

    # King must be on its home square
    if row != back_row or col != 4:
        return moves

    # King must not currently be in check
    if is_in_check(board, color):
        return moves

    # King-side castling
    if board.castling.get(color + 'K'):
        f_sq = sq(5, back_row)
        g_sq = sq(6, back_row)
        h_sq = sq(7, back_row)
        if (board.is_empty(f_sq) and board.is_empty(g_sq)
                and board.piece_at(h_sq) == color + 'R'):
            # King must not pass through or land on attacked square
            if (not _square_attacked(board, f_sq, color)
                    and not _square_attacked(board, g_sq, color)):
                moves.append((square, g_sq, 'castle_k'))

    # Queen-side castling
    if board.castling.get(color + 'Q'):
        d_sq = sq(3, back_row)
        c_sq = sq(2, back_row)
        b_sq = sq(1, back_row)
        a_sq = sq(0, back_row)
        if (board.is_empty(d_sq) and board.is_empty(c_sq)
                and board.is_empty(b_sq)
                and board.piece_at(a_sq) == color + 'R'):
            if (not _square_attacked(board, d_sq, color)
                    and not _square_attacked(board, c_sq, color)):
                moves.append((square, c_sq, 'castle_q'))

    return moves


def _super_pawn_moves(board, square: str, color: str) -> list[tuple]:
    """Super Pawn = Queen rays + Knight jumps."""
    moves = _sliding_moves(board, square, color, QUEEN_DIRS)
    moves += _knight_moves(board, square, color)
    return moves


# ── Square-attack detection ───────────────────────────────────────────────────

def _square_attacked(board, square: str, defending_color: str) -> bool:
    """
    Return True if any enemy piece attacks `square`.
    defending_color is the side that OWNS the square (we want to know if
    the enemy is attacking it).
    """
    enemy = 'b' if defending_color == 'w' else 'w'
    col, row = coords(square)

    # Attacked by enemy pawn?
    pawn_dir = 1 if defending_color == 'w' else -1   # direction enemy pawn attacks FROM
    for dc in (-1, 1):
        pc, pr = col + dc, row + pawn_dir
        if on_board(pc, pr):
            p = board.piece_at(sq(pc, pr))
            if p == enemy + 'P':
                return True

    # Attacked by enemy knight?
    for dc, dr in KNIGHT_MOVES:
        tc, tr = col + dc, row + dr
        if on_board(tc, tr):
            p = board.piece_at(sq(tc, tr))
            if p == enemy + 'N':
                return True

    # Attacked by enemy king?
    for dc, dr in QUEEN_DIRS:
        tc, tr = col + dc, row + dr
        if on_board(tc, tr):
            p = board.piece_at(sq(tc, tr))
            if p == enemy + 'K':
                return True

    # Attacked along rook rays (rook or queen)?
    for dc, dr in ROOK_DIRS:
        tc, tr = col + dc, row + dr
        while on_board(tc, tr):
            p = board.piece_at(sq(tc, tr))
            if p is not None:
                if p in (enemy + 'R', enemy + 'Q', enemy + 'S'):
                    return True
                break
            tc += dc
            tr += dr

    # Attacked along bishop rays (bishop or queen)?
    for dc, dr in BISHOP_DIRS:
        tc, tr = col + dc, row + dr
        while on_board(tc, tr):
            p = board.piece_at(sq(tc, tr))
            if p is not None:
                if p in (enemy + 'B', enemy + 'Q', enemy + 'S'):
                    return True
                break
            tc += dc
            tr += dr

    # Attacked by enemy Super Pawn via knight jump?
    for dc, dr in KNIGHT_MOVES:
        tc, tr = col + dc, row + dr
        if on_board(tc, tr):
            p = board.piece_at(sq(tc, tr))
            if p == enemy + 'S':
                return True

    return False


# ── Check detection ───────────────────────────────────────────────────────────

def is_in_check(board, color: str) -> bool:
    king_sq = board.find_king(color)
    if king_sq is None:
        return False
    return _square_attacked(board, king_sq, color)


# ── Pseudo-move dispatcher ────────────────────────────────────────────────────

def get_pseudo_moves(board, square: str) -> list[tuple]:
    """All moves for the piece on `square` without checking own-king safety."""
    piece = board.piece_at(square)
    if piece is None:
        return []
    color, kind = piece[0], piece[1]

    if kind == 'P': return _pawn_moves(board, square, color)
    if kind == 'N': return _knight_moves(board, square, color)
    if kind == 'B': return _sliding_moves(board, square, color, BISHOP_DIRS)
    if kind == 'R': return _sliding_moves(board, square, color, ROOK_DIRS)
    if kind == 'Q': return _sliding_moves(board, square, color, QUEEN_DIRS)
    if kind == 'K': return _king_moves(board, square, color)
    if kind == 'S': return _super_pawn_moves(board, square, color)
    return []


# ── Legal-move filter ─────────────────────────────────────────────────────────

def get_legal_moves(board, square: str) -> list[tuple]:
    """
    Return only moves that do not leave own king in check.
    Each move: (from_sq, to_sq, flag)
    """
    piece = board.piece_at(square)
    if piece is None:
        return []
    color = piece[0]

    legal = []
    for move in get_pseudo_moves(board, square):
        from_sq, to_sq, flag = move

        # Determine promotion piece for apply_move (use Queen as stand-in;
        # actual piece chosen by player later — what matters here is legality)
        promo = flag[-1] if flag and flag.startswith('promo_') else None

        record = board.apply_move(from_sq, to_sq, promotion=promo)
        if not is_in_check(board, color):
            legal.append(move)
        board.undo_move(record)

    return legal


def get_all_legal_moves(board, color: str) -> list[tuple]:
    """Return all legal moves for every piece of `color`."""
    all_moves = []
    for square in list(board.pieces_of(color).keys()):
        all_moves.extend(get_legal_moves(board, square))
    return all_moves


# ── Game-state queries ────────────────────────────────────────────────────────

def is_checkmate(board, color: str) -> bool:
    return is_in_check(board, color) and len(get_all_legal_moves(board, color)) == 0


def is_stalemate(board, color: str) -> bool:
    return (not is_in_check(board, color)
            and len(get_all_legal_moves(board, color)) == 0)


def is_insufficient_material(board) -> bool:
    """
    True when neither side can possibly deliver checkmate.
    Covers: K vs K, K+B vs K, K+N vs K.
    Super Pawn is always sufficient, so return False if any S exists.
    """
    pieces = list(board.grid.values())

    # Super Pawn, Queen, Rook, or multiple Pawns → always sufficient
    for p in pieces:
        if p[1] in ('Q', 'R', 'P', 'S'):
            return False

    # Count minor pieces
    minor = [p for p in pieces if p[1] in ('B', 'N')]
    return len(minor) <= 1


# ── Move notation helper (for move log) ──────────────────────────────────────

def move_to_notation(board_before_move, from_sq: str, to_sq: str,
                     flag: str | None) -> str:
    """
    Very lightweight algebraic notation string for the move log sidebar.
    Not full SAN — just enough to be readable.
    """
    piece   = board_before_move.piece_at(from_sq)
    if piece is None:
        return f"{from_sq}-{to_sq}"
    kind    = piece[1]
    capture = board_before_move.piece_at(to_sq) is not None or flag == 'ep'
    sep     = 'x' if capture else '-'

    if flag and flag.startswith('castle'):
        return 'O-O' if flag == 'castle_k' else 'O-O-O'

    prefix = '' if kind == 'P' else kind
    suffix = ''
    if flag and flag.startswith('promo_'):
        suffix = '=' + flag[-1]

    return f"{prefix}{from_sq}{sep}{to_sq}{suffix}"