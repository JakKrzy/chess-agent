import random
import sys
import chess

class Chess:
    def __init__(self):
        self.board: chess.Board = chess.Board()
        
    def update(self, uci_move):
        try:
            move = chess.Move.from_uci(uci_move)
        except ValueError:
            raise "WrongMove"

        if move not in self.board.legal_moves:
            raise "WrongMove"
            
        self.board.push(move)
        out = self.board.outcome()
        if out is None:
            return None
        if out.winner is None:
            return 0
        if out.winner:
            return -1
        else:
            return +1
        
    def do_move(self, uci_move):
        new_state = copy(self)
        new_state.update(uci_move)
        return new_state
    
    def moves(self):
        return [str(m) for m in self.board.legal_moves]
        
    def draw(self):
        print (self.board)    

def copy(state: Chess):
    n_state = Chess()
    n_state.board = state.board.copy()
    return n_state
