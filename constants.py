# --- Window ---
WINDOW_WIDTH  = 900
WINDOW_HEIGHT = 560
BOARD_SIZE    = 512          # 8 × 64
SQUARE_SIZE   = BOARD_SIZE // 8   # 64
BOARD_OFFSET_X = 24          # left margin so board sits nicely
BOARD_OFFSET_Y = (WINDOW_HEIGHT - BOARD_SIZE) // 2   # vertically centred

# Sidebar
SIDEBAR_X     = BOARD_OFFSET_X + BOARD_SIZE + 16
SIDEBAR_WIDTH = WINDOW_WIDTH - SIDEBAR_X - 12

# --- Colours ---
# Board
LIGHT_SQUARE   = (240, 217, 181)   # classic cream
DARK_SQUARE    = (181, 136,  99)   # classic brown
HIGHLIGHT_SEL  = (247, 247, 105, 180)  # selected square  (yellow, semi-transparent)
HIGHLIGHT_MOVE = ( 20, 200,  20, 140)  # legal-move dot   (green, semi-transparent)
HIGHLIGHT_CHECK= (220,  50,  50, 160)  # king-in-check    (red)
LAST_MOVE_FROM = (205, 210, 106, 140)
LAST_MOVE_TO   = (205, 210, 106, 180)

# UI
BG_DARK        = ( 30,  30,  35)
BG_SIDEBAR     = ( 42,  42,  50)
BG_CARD        = ( 52,  52,  62)
ACCENT_GOLD    = (212, 175,  55)
ACCENT_SUPER   = (180,  80, 220)   # purple tint for Super-Pawn related UI
TEXT_PRIMARY   = (235, 235, 235)
TEXT_SECONDARY = (160, 160, 170)
TEXT_DARK      = ( 20,  20,  25)
BORDER_COLOR   = ( 70,  70,  85)
WHITE_COLOR    = (255, 255, 255)
BLACK_COLOR    = (  0,   0,   0)

# Status colours
STATUS_NORMAL  = (100, 200, 120)
STATUS_CHECK   = (230, 100,  60)
STATUS_MATE    = (200,  50,  50)
STATUS_THINKING= (100, 160, 240)

# --- Piece codes ---
# Colour prefix: 'w' = white, 'b' = black
# Type suffix  : K Q R B N P S   (S = Super Pawn)
PIECES = ['K', 'Q', 'R', 'B', 'N', 'P', 'S']

# --- Piece values (for evaluation) ---
PIECE_VALUES = {
    'K': 20000,
    'Q':     9,
    'R':     5,
    'B':     3,
    'N':     3,
    'P':     1,
    'S':    11,   # Queen(9) + Knight(3) – single-piece discount
}

# --- Starting positions ---
# Normal side (standard chess)
NORMAL_WHITE_BACK = {
    'a1': 'wR', 'b1': 'wN', 'c1': 'wB', 'd1': 'wQ',
    'e1': 'wK', 'f1': 'wB', 'g1': 'wN', 'h1': 'wR',
}
NORMAL_BLACK_BACK = {
    'a8': 'bR', 'b8': 'bN', 'c8': 'bB', 'd8': 'bQ',
    'e8': 'bK', 'f8': 'bB', 'g8': 'bN', 'h8': 'bR',
}

# Super-Pawn side back rank
# White: K=h1  Q=g1  S=f1
SUPER_WHITE_BACK = {
    'f1': 'wS', 'g1': 'wQ', 'h1': 'wK',
}
# Black: K=h8  Q=g8  S=f8
SUPER_BLACK_BACK = {
    'f8': 'bS', 'g8': 'bQ', 'h8': 'bK',
}

# Pawn ranks
NORMAL_WHITE_PAWNS = {f'{c}2': 'wP' for c in 'abcdefgh'}
NORMAL_BLACK_PAWNS = {f'{c}7': 'bP' for c in 'abcdefgh'}
SUPER_WHITE_PAWNS  = {f'{c}2': 'wP' for c in 'abcdefgh'}
SUPER_BLACK_PAWNS  = {f'{c}7': 'bP' for c in 'abcdefgh'}

# --- Directions ---
ROOK_DIRS   = [(-1,0),(1,0),(0,-1),(0,1)]
BISHOP_DIRS = [(-1,-1),(-1,1),(1,-1),(1,1)]
QUEEN_DIRS  = ROOK_DIRS + BISHOP_DIRS
KNIGHT_MOVES= [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]

# --- Game states ---
STATE_START     = 'start'
STATE_PLAYING   = 'playing'
STATE_PROMOTION = 'promotion'
STATE_GAME_OVER = 'game_over'

# --- AI ---
AI_DEPTH = 4

# --- Frame rate ---
FPS = 60