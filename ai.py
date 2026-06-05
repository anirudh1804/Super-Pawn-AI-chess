"""
ai.py
Minimax engine with alpha-beta pruning for Super Pawn Chess.

Public API
----------
get_best_move(board, depth, ai_color) -> (from_sq, to_sq, flag) | None
"""

import math
from moves    import get_all_legal_moves, is_checkmate, is_stalemate
from evaluate import evaluate
from constants import PIECE_VALUES


def _move_score(board, move) -> int:
    from_sq, to_sq, flag = move
    score = 0
    if flag and flag.startswith('promo_'):
        score += {'Q': 90, 'R': 50, 'B': 30, 'N': 30}.get(flag[-1], 0)
    if flag and flag.startswith('castle'):
        score += 10
    victim   = board.piece_at(to_sq)
    attacker = board.piece_at(from_sq)
    if victim:
        v_val = PIECE_VALUES.get(victim[1],   0)
        a_val = PIECE_VALUES.get(attacker[1], 1) if attacker else 1
        score += 10 * v_val - a_val
    if flag == 'ep':
        score += 10
    return score


def _order_moves(board, moves):
    return sorted(moves, key=lambda m: _move_score(board, m), reverse=True)


def _minimax(board, depth, alpha, beta, maximising):
    color = 'w' if maximising else 'b'

    if depth == 0:
        return evaluate(board)

    moves = get_all_legal_moves(board, color)
    if not moves:
        if is_checkmate(board, color):
            return (-9999.0 + (10 - depth)) if maximising else (9999.0 - (10 - depth))
        return 0.0

    moves = _order_moves(board, moves)

    if maximising:
        best = -math.inf
        for from_sq, to_sq, flag in moves:
            promo  = flag[-1] if flag and flag.startswith('promo_') else None
            record = board.apply_move(from_sq, to_sq, promotion=promo)
            val    = _minimax(board, depth - 1, alpha, beta, False)
            board.undo_move(record)
            if val > best:
                best = val
            if best > alpha:
                alpha = best
            if beta <= alpha:
                break
        return best
    else:
        best = math.inf
        for from_sq, to_sq, flag in moves:
            promo  = flag[-1] if flag and flag.startswith('promo_') else None
            record = board.apply_move(from_sq, to_sq, promotion=promo)
            val    = _minimax(board, depth - 1, alpha, beta, True)
            board.undo_move(record)
            if val < best:
                best = val
            if best < beta:
                beta = best
            if beta <= alpha:
                break
        return best


def get_best_move(board, depth, ai_color):
    """
    Returns (from_sq, to_sq, flag) for the best move, or None.
    """
    moves = get_all_legal_moves(board, ai_color)
    if not moves:
        return None

    moves      = _order_moves(board, moves)
    maximising = (ai_color == 'w')
    best_move  = None
    best_val   = -math.inf if maximising else math.inf

    for from_sq, to_sq, flag in moves:
        promo  = flag[-1] if flag and flag.startswith('promo_') else None
        record = board.apply_move(from_sq, to_sq, promotion=promo)
        val    = _minimax(board, depth - 1, -math.inf, math.inf, not maximising)
        board.undo_move(record)

        if maximising and val > best_val:
            best_val  = val
            best_move = (from_sq, to_sq, flag)
        elif not maximising and val < best_val:
            best_val  = val
            best_move = (from_sq, to_sq, flag)

    return best_move