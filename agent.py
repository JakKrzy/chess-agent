#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import random
import sys

from state import *
import chess
import chess.polyglot

PIECE_VALUES = { chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9 }

class Player(object):
    MAX_DEPTH = 2
    INF = 1000000

    def __init__(self):
        self.opening_book = chess.polyglot.MemoryMappedReader('./baron30.bin')
        self.reset()

    def reset(self):
        self.game = Chess()
        self.my_player = 1
        self.my_color = chess.BLACK
        self.say('RDY')

    def say(self, what):
        sys.stdout.write(what)
        sys.stdout.write('\n')
        sys.stdout.flush()

    def hear(self):
        line = sys.stdin.readline().split()
        return line[0], line[1:]

    def loop(self):
        while True:
            cmd, args = self.hear()
            if cmd == 'HEDID':
                unused_move_timeout, unused_game_timeout = args[:2]
                move = args[2]
                self.game.update(move)
                print(self.game.board)
            elif cmd == 'ONEMORE':
                self.reset()
                continue
            elif cmd == 'BYE':
                break
            else:
                assert cmd == 'UGO'
                self.my_player = 0
                self.my_color = chess.WHITE

            try:
                opening_book_entry = self.opening_book.choice(self.game.board)
                if opening_book_entry:
                    move = opening_book_entry.move.uci()
            except:
                moves = self.game.moves()
                move = max(moves, key=lambda m: self.min_value(self.game.do_move(m), -Player.INF, Player.INF, 0))

            self.game.update(move)
            self.say('IDO ' + move)
            print(self.game.board)
    
    def evaluate_material(self, game: Chess, player: chess.Color):
        res = 0
        for piece, value in PIECE_VALUES.items():
            for _ in game.board.pieces(piece, player):
                res += value
        return res

    def evaluate_mobility(self, game: Chess):
        if game.board.turn == self.my_color:
            return game.board.legal_moves.count()
        game.board.push(chess.Move.null())
        res = game.board.legal_moves.count()
        game.board.pop()
        return res
    
    def evaluate_center_control(self, game: Chess):
        center_squares = { chess.D4, chess.D5, chess.E4, chess.E5 }
        outer_center_squares = { chess.D3, chess.D6, chess.C6,
                                chess.C5, chess.C4, chess.C3,
                                chess.E6, chess.E3, chess.F6,
                                chess.F5, chess.F4, chess.F3 }
        res = 0
        for move in game.board.legal_moves:
            if move.to_square in center_squares: res += 2
            elif move.to_square in outer_center_squares: res += 1
        
        for square in center_squares:
            p = game.board.piece_at(square)
            if p and p.color == self.my_color:
                if p.piece_type in PIECE_VALUES.keys():
                    res += PIECE_VALUES[p.piece_type]
                if p.piece_type == chess.PAWN:
                    res += 5

        for square in outer_center_squares:
            p = game.board.piece_at(square)
            if p and p.color == self.my_color:
                if p.piece_type in PIECE_VALUES.keys():
                    res += PIECE_VALUES[p.piece_type]
                if p.piece_type == chess.PAWN:
                    res += 5
        return res
    
    def evaluate_pawn_shield(self, game: Chess):
        pawn_shields_for_king = { 
            chess.G1: (chess.F2, chess.G2, chess.H2),
            chess.H1: (chess.F2, chess.G2, chess.H2),
            chess.B1: (chess.C2, chess.B2, chess.A2),
            chess.A1: (chess.C2, chess.B2, chess.A2),
            chess.A8: (chess.C7, chess.B7, chess.A7),
            chess.B8: (chess.C7, chess.B7, chess.A7),
            chess.G8: (chess.F7, chess.G7, chess.H7),
            chess.H8: (chess.F7, chess.G7, chess.H7)}
        
        res = 0
        king_squares = game.board.pieces(chess.KING, self.my_color)
        for king_sq in king_squares:
            if king_sq in pawn_shields_for_king.keys():
                for pawn_sq in pawn_shields_for_king[king_sq]:
                    if game.board.piece_type_at(pawn_sq) == chess.PAWN:
                        res += 1
        return res
    
    def evaluate_threats(self, game: Chess, player: chess.Color):
        _game = copy(game)
        if game.board.turn == player:
            _game.board.push(chess.Move.null())
        
        res = 0
        for move in _game.board.legal_moves:
            piece = _game.board.piece_at(move.to_square)
            if piece and piece.color == self.my_color:
                if piece.piece_type == chess.KING:
                    res += 20
                else:
                    res += PIECE_VALUES[piece.piece_type]
        return res
    
    def evaluate_piece_activation(self, game: Chess, player: chess.Color):
        starting_piece_positions = {
            chess.WHITE: {
                chess.ROOK:   { chess.H1, chess.A1 },
                chess.KNIGHT: { chess.G1, chess.B1 },
                chess.BISHOP: { chess.F1, chess.C1 },
                chess.QUEEN:  { chess.D1 }
            },
            chess.BLACK: {
                chess.ROOK:   { chess.H8, chess.A8 },
                chess.KNIGHT: { chess.G8, chess.B8 },
                chess.BISHOP: { chess.F8, chess.C8 },
                chess.QUEEN:  { chess.D8 }
            }}
        
        res = 0
        for piece, starting_positions in starting_piece_positions[player].items():
            for square in starting_positions:
                p = game.board.piece_at(square)
                if p and p.color == player and p.piece_type == piece:
                    res += PIECE_VALUES[p.piece_type]
        return res

    def evaluate(self, game: Chess):
        return ( 5 * (self.evaluate_material(game, self.my_color) - self.evaluate_material(game, not self.my_color))
                + 2 * self.evaluate_mobility(game)
                + 2 * self.evaluate_center_control(game)
                + 1 * self.evaluate_pawn_shield(game)
                - 4 * self.evaluate_threats(game, self.my_color)
                + 4 * self.evaluate_threats(game, not self.my_color)
                - 3 * self.evaluate_piece_activation(game, self.my_color))
    
    def min_value(self, game: Chess, alpha, beta, depth):
        if depth >= Player.MAX_DEPTH: return self.evaluate(game)

        outcome = game.board.outcome()
        if outcome:
            if outcome.winner == self.my_color:
                return Player.INF
            elif outcome.winner == (not self.my_color):
                return -Player.INF

        value = Player.INF
        for s in [game.do_move(m) for m in game.moves()]:
            value = min(value, self.max_value(s, alpha, beta, depth + 1))
            if value <= alpha:
                return value
            beta = min(beta, value)
        return value
    
    def max_value(self, game: Chess, alpha, beta, depth):
        if depth >= Player.MAX_DEPTH: return self.evaluate(game)

        outcome = game.board.outcome()
        if outcome:
            if outcome.winner == self.my_color:
                return Player.INF
            elif outcome.winner == (not self.my_color):
                return -Player.INF
        
        value = -Player.INF
        for s in [game.do_move(m) for m in game.moves()]:
            value = max(value, self.min_value(s, alpha, beta, depth + 1))
            if value >= beta:
                return value
            alpha = max(alpha, value)
        return value

if __name__ == '__main__':
    player = Player()
    player.loop()
