#!/usr/bin/env python3


import logging
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger("backend")

import random
random.seed(a=2)  # TODO: seed hardcoded for reproductibility while debugging. REMOVE at will

import math as m
from operator import itemgetter
import itertools
import copy
from contextlib import suppress



# ##############################################################################
# settings
# ##############################################################################
N = 50 # [m] rows
M = 100 # [m] columns
V = 5 # [m/s] velocity of [European] unladden swallow is 11, but let's limit this


# ##############################################################################
# tools
# ##############################################################################

def frange(start, stop, step):
    yield from itertools.takewhile(
        lambda x: x < stop,
        itertools.count(start, step)
    )

infinity = float("inf")

def radians_normalize(x):
    x = float(x)
    res = x % (m.pi*2)
    log.debug("normalizing to range [0;2π): %.4f → %.4f", x, res)
    return res


# ##############################################################################
# board
# ##############################################################################
class Board:
    class BoardOYProxy:
        def __init__(self, column, columns_count):
            self.column = column
            self.columns_count = columns_count
        def __getitem__(self, colid):
            colid = int(colid) % self.columns_count
            return self.column[colid]
        def __setitem__(self, colid, val):
            colid = int(colid) % self.columns_count
            self.column[colid] = val

    @staticmethod
    def _newboard(rows,cols):
        return [[None for col in range(rows)] for row in range(cols)]

    def __init__(self, rows, cols):
        self.rows = rows
        self.cols = cols
        self.matrix = self._newboard(rows,cols)

    def __getitem__(self, rowid):
        return Board.BoardOYProxy(self.matrix[int(rowid) % self.rows], self.cols)

    def step(self):
        new_matrix = self._newboard(self.rows, self.cols)
        for rowid, row in enumerate(self.matrix):
            for colid, elem in enumerate(row):
                with suppress(AttributeError):
                    x,y = elem.step(rowid, colid)
                    new_matrix[x % M][y % N] = elem
        self.matrix = new_matrix

    def __str__(self):
        return ''.join(self._str_helper())  # works "like stringbuilder"

    def _str_helper(self):
        def draw_point(x):
            return str(x or ' ')
        header = "+" + M*'-' + "+"
        yield header
        # TODO [kgdk] 28 mar 2015: board colours
        for row in self.matrix:
            yield '|'
            for elem in row:
                yield draw_point(elem)
            yield '|\n'
        yield header

    def add_random_bird(self):
        while True:
            x = random.randrange(0, self.rows)
            y = random.randrange(0, self.cols)
            if not self[x][y]:
                a = radians_normalize(random.uniform(0, 2*m.pi))
                self[x][y] = Bird(a)
                log.info("adding random bird. XY = (%d,%d) angle = %.4f", x, y, a)
                break
            else:
                log.debug("adding random bird fial'd: XY = (%d,%d) is already occupied. retry", x, y)


# ##############################################################################
# 🐦
# ##############################################################################
class Bird:
    def __init__(self, direction):
        self.direction = radians_normalize(direction)
    def __str__(self):
        pi  = m.pi
        pi2 = m.pi * 0.5
        pi4 = m.pi * 0.25
        pi8 = m.pi * 0.125
        direction = radians_normalize(self.direction - pi8)
        ranges = [
            (0    , 1*pi8, '↘' ),
            (1*pi8, pi4,   '↓' ),
            (pi4,   3*pi8, '↙' ),
            (3*pi8, pi2,   '←' ),
            (pi2,   5*pi8, '↖' ),
            (5*pi8, 3*pi4, '↑' ),
            (3*pi4, 7*pi8, '↗' ),
            (7*pi8, 2*pi,  '→' )
        ]
        for r_from, r_to, res in ranges:
            if r_from <= direction < r_to:
                log.debug("for direction %.4f returning %s", self.direction, res)
                return res
        else:
            log.error("whoopsie, direction %.4f did not fell into any of the ranges. Mea culpa…  — kgadek", self.direction)
            raise ArithmeticError()
    def step(self, old_x, old_y):
        def rand_round(x):
            if x.is_integer():
                return int(x)
            low = m.floor(x)
            hi  = m.ceil(x)
            if random.uniform(low, hi) <= x:
                return low
            else:
                return hi
        new_x = rand_round(old_x + m.cos(self.direction) * V)
        new_y = rand_round(old_y + m.sin(self.direction) * V)
        log.debug("old: (%d,%d) new: (%d,%d)", old_x, old_y, new_x, new_y)
        return new_x, new_y

    @staticmethod
    def distance_function_find_max(a, b):
        a = float(a)
        b = float(b)
        # TODO [kgdk] 28 mar 2015: użyć metody Newtona
        def aux(x): return abs(m.tan(1/(a+x)) * (a+x)**2 - x * m.log(x))
                            #  ^-- this is a deriv. of the main function
        max_arg, min_deriv = min( ( (x1, aux(x1))
                                    for x1 in frange(0.1, 100.0, 0.1)
                                ), key=itemgetter(1) )
        max_val = m.log(max_arg) * m.sin(1./(a+max_arg))
        log.debug("distance_function max value for a=%.4f, b=%.4f found: f(%.4f) ≃ %.4f",
                  a, b, max_arg, max_val)
        log.debug("(note that this may not be precise!)")
        return max_arg, max_val

    @staticmethod
    def distance_function(x,
                          a:'modifies the point of maximum value' = 1.0,
                          b:'modifies the zero-point'             = 1.0,
                         ):
        x = float(x)
        if x <= 0.0:
            log.debug("distance_function(%.5f) = -∞", x)
            return infinity
        log.debug("distance_function(%.5f) = %.5f", x, m.log(x) * m.sin(1./(a+x)))
        return m.log(x) * m.sin(1./(a+x))


# ##############################################################################
# the program
# ##############################################################################
def main():
    board = Board(M, N)
    board.add_random_bird()
    board.add_random_bird()
    board.add_random_bird()
    print(board)
    board.step()
    print(board)
    # board = new_board()
    # board[30][40] = Bird(0)
    # print_board(board)

    # newboard = new_board()
    # for rowid, row in enumerate(board):
    #     for colid, elem in enumerate(row):
    #         with suppress(AttributeError):
    #             x,y = elem.step(rowid, colid)
    #             newboard[x % M][y % N] = elem
    # print_board(newboard)


if __name__ == '__main__':
    main()