#!/usr/bin/env python3


import logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("backend")

import random
random.seed(a=2)  # TODO: seed hardcoded for reproductibility while debugging. REMOVE at will

import math as m
import itertools
import copy
from operator   import itemgetter
from functools  import partial
from contextlib import suppress

import bottle
from bottle import route, run, template, response, static_file

import json

from pathlib import Path


# ##############################################################################
# settings
# ##############################################################################
N = 50 # [m] rows
M = 100 # [m] columns
V = 4 # [m/s] velocity of [European] unladden swallow is 11, but let's limit this


# ##############################################################################
# tools
# ##############################################################################

def frange(start, stop, step):
    """ Helper. Generate range of floats.
    >>> list(frange(1.0, 2.0, 0.25))
    [1.0, 1.25, 1.5, 1.75]
    """
    yield from itertools.takewhile(
        lambda x: x < stop,
        itertools.count(start, step)
    )

infinity = float("inf")

def radians_normalize(x):
    """ Normalize to range [0,2π).
    
    >>> radians_normalize(0)
    0.0
    >>> radians_normalize(2*m.pi)
    0.0
    >>> radians_normalize(3*m.pi+0.5)
    3.641592653589793
    """
    x = float(x)
    res = x % (m.pi*2)
    log.debug("normalizing to range [0;2π): %.4f → %.4f", x, res)
    return res

def df(x,a,b):
    """ First derivative of distance function """
    div_bx = 1./(b+x)
    return 1./x * m.sin(div_bx) - m.log(a*x) * m.cos(div_bx) * div_bx**2

def ddf(x,a,b):
    """ Second derivative of distance function """
    div_bx = 1./(b+x)
    return m.log(a * x) * (2*m.cos(div_bx) * div_bx**3 - m.sin(div_bx) * div_bx**4) - m.sin(div_bx) / x**2 - 2*m.cos(div_bx) * div_bx**2 / x

def f(x,a,b):
    """ The distance function. This drives the bird.

    >>> all( f(1/a, a, 1) == 0.0 for a in range(1,15) )
    True

    # Assert the maximum of a function is at the right place

    >>> newton_find(partial(df,a=3,b=5), partial(ddf,a=3,b=5), 1./3)
    3.6303997623856503

    # Verify (sort of) that function is strictly decreasing

    >>> f(100, 1, 1) > f(1000, 1, 1) > f(10000, 1, 1) > f(100000, 1, 1) > f(1000000, 1, 1)
    True

    >>> f(0, 1, 1)
    -inf
    """
    try:
        return m.log(a * x) * m.sin(1./(b+x))
    except Exception as e:
        return -infinity
    

def newton_find(f, df, x, iters=10):
    log.debug("newton_find x=%.4f", x)
    for i in range(iters):
        log.debug("  iteration %d, x=%.4f", i, x)
        log.debug("    df(%.4f) = %.4f", x, df(x))
        log.debug("    f(%.4f) = %.4f", x, f(x))
        if df(x) == 0:
            log.debug("    df(%.4f) == 0, returning %.4f", x, x)
            return x
        x -= f(x)/df(x)
    return x

def euclid_dist(xy1, xy2):
    """ Euclidean distance.
    >>> euclid_dist((0,0), (0,0))
    0.0

    >>> euclid_dist((1,0), (0,0))
    1.0

    # euclid_dist is commutative

    >>> all(  euclid_dist((x1,y1),(x2,y2)) == euclid_dist((x2,y2),(x1,y1))  for x1,y1,x2,y2 in itertools.product(list(frange(-2.8, 2.8, 0.7)), repeat=4)  )
    True
    """
    (x1,x2) = xy1
    (y1,y2) = xy2
    return m.sqrt((x1-x2)**2 + (y1-y2)**2)

def rand_round(x):
    """ Helper: convert float to int in reasonable way.
    If the number is integer (up to given precision), return the int.
    Otherwise, randomly chose if to return the bigger or the smaller
    int (ceil or floor).
    >>> rand_round(0)
    0
    >>> rand_round(0.001)
    0
    >>> rand_round(-0.001)
    0
    >>> random.seed(1); rand_round(0.9)
    0
    >>> random.seed(2); rand_round(0.9)
    1
    """
    if abs(x - round(x)) < 0.01:
        return round(x)
    low = m.floor(x)
    hi  = m.ceil(x)
    if random.uniform(float(low), float(hi)) <= x:
        return low
    else:
        return hi

# ##############################################################################
# board
# ##############################################################################
class Board:
    def __init__(self, rows, cols):
        log.debug("Board.__init__(%d, %d)",rows,cols)
        self.rows = rows
        self.cols = cols
        self.matrix = self._newboard(rows,cols)
        self.birds = []
        self.blocks = []

    @staticmethod
    def _newboard(rows,cols):
        """ Helper, creates new empty board representation. """
        return [[None for col in range(cols)]
                for row in range(rows)
               ]
    
    class BoardColumnAccessProxy:
        """ The proxy that allows nice syntax for accessing board.
        You can therefore access with floats (will be rounded down) or outside
        of the board (it wraps around).
        """
        def __init__(self, column, cols_count):
            log.debug("Board.BoardColumnAccessProxy.__init__(column, %d)", cols_count)
            self.column = column
            self.cols_count = cols_count
        def __getitem__(self, colid):
            colid = int(colid) % self.cols_count
            return self.column[colid]
        def __setitem__(self, colid, val):
            colid = int(colid) % self.cols_count
            self.column[colid] = val

    def __getitem__(self, rowid):
        """ Nice accessor for board.
        Works nicely with BoardColumnAccessProxy to offer:
         * accessing with floats - they will be just truncated
         * accessing with out-of-bounds values – the board wraps around (forms torus)
        >>> a = Board(3,4); a[0][1] = 123; a[0][1]
        123
        >>> a = Board(3,4); a[0][1] = 123; a[0+3*1000][1-4*667]
        123
        >>> a = Board(3,4); a[0.5][1.2] = 123; a[0.99][1.99+4*667]
        123
        """
        log.debug("accessing %d but actually %d limit %d", rowid, int(rowid) % self.rows, len(self.matrix))
        return Board.BoardColumnAccessProxy(self.matrix[int(rowid) % self.rows], self.cols)

    def step(self):
        """ Perform one step of the simulation. """
        log.debug("Board.step")
        old_board = self.matrix
        old_birds = self.birds
        self.matrix = self._newboard(self.rows, self.cols)
        self.birds  = []
        for row, col, block in self.blocks:
            self[row][col] = block
        for row, col, bird in old_birds:
            nrow, ncol = bird.step(row, col)
            self[nrow][ncol] = bird
            self.birds.append((nrow, ncol, bird))

    def __str__(self):
        """ Pretty-printer for the console.
        >>> print(Board(2,5))
        +-----+
        |     |
        |     |
        +-----+
        """
        def helper():
            header = "+" + self.cols*'-' + "+"
            yield header + "\n"
            for row in self.matrix:
                yield '|'
                for elem in row:
                    yield str(elem or ' ')  # TODO [kgdk] 28 mar 2015: board colours for console?
                yield '|\n'
            yield header
        return ''.join(helper())  # works a bit like "like stringbuilder"

    def tojson(self):
        """ Returns a list of bird coordinates in order suited for a particular use.
        
        >>> Board(2,5).tojson()
        '[]'

        >>> board=Board(10, 20); board.add_bird(2,1,0);                                                                       json.loads(board.tojson()) == [{"x": 2, "y": 1, "xy": 12, "dir": 0.0}]
        True

        >>> board=Board(10, 20); board.add_bird(2,1,0); board.add_bird(1,2,0);                                                json.loads(board.tojson()) == [{'y': 1, 'x': 2, 'dir': 0.0, 'xy': 12}, {'y': 2, 'x': 1, 'dir': 0.0, 'xy': 21}]
        True

        >>> from backend import *; board=Board(10, 20); board.add_bird(2,1,0); board.add_bird(1,2,0); board.add_bird(0,0,0);  json.loads(board.tojson()) == [{'y': 0, 'x': 0, 'dir': 0.0, 'xy': 0}, {'y': 1, 'x': 2, 'dir': 0.0, 'xy': 12}, {'y': 2, 'x': 1, 'dir': 0.0, 'xy': 21}]
        True
        """
        elems = [ {"x": y, "y": x, "xy": x*self.rows + y, "disp": elem.disp_num()}
                  for y, row
                  in enumerate(self.matrix)
                  for x, elem
                  in enumerate(row)
                  if elem
                ]
        elems = sorted(elems, key=lambda dct: dct['xy'])
        return json.dumps(elems)

    def add_random_bird(self):
        """ Generate a random Bird and place it on the board. """
        while True:
            x = random.randrange(0, self.rows)
            y = random.randrange(0, self.cols)
            if not self[x][y]:
                a = random.uniform(0, 2*m.pi)
                self.add_bird(x, y, a)

                log.info("adding random bird randomly to the board. row,col = (%d,%d) angle = %.4f", x, y, a)
                break
            else:
                log.debug("adding random bird fial'd: position (%d,%d) is already occupied. Retrying", x, y)

    def add_random_block(self):
        """ Generate a random Bird and place it on the board. """
        while True:
            x = random.randrange(0, self.rows)
            y = random.randrange(0, self.cols)
            if not self[x][y]:
                self.add_block(x, y)

                log.info("adding random block randomly to the board. row,col = (%d,%d)", x, y)
                break
            else:
                log.debug("adding random block fial'd: position (%d,%d) is already occupied. Retrying", x, y)

    def add_bird(self, x, y, a):
        bird = Bird(radians_normalize(a))
        self[x][y] = bird
        self.birds.append((x,y,bird))

    def add_block(self, x, y):
        block = Block()
        self[x][y] = block
        self.blocks.append((x,y,block))

    @staticmethod
    def distances_wrapped_on_torus(x, y, xx, yy, rows, cols):
        """ Distances on torus.
        Ok, so this is interesting. Since our board is wrapped around, we have two choices for the
        behaviour of influences:
          * when two birds are half-board apart, then moving slightly left & right completely
            changes the direction of influence,
          * even though two birds are close to each other, we take into account the influence
            when going around the wrapping.
        I've picked the second one. Shall be more fun :)
        
        >>> list( Board.distances_wrapped_on_torus(0, 0, 1, 1, 3, 5) )
        [(1, 1), (1, -4), (-2, -4), (-2, 1)]

        #  |        |        |        |
        #  |        |        |        +- distance when wrapping around top border
        #  |        |        +---------- distance when wrapping around top and left border
        #  |        +------------------- distance when wrapping around left border
        #  +---------------------------- simple distance: 1 on OX, 1 on OY
        #
        #
        #                      A    A    A
        #  +-----+              B    B    B                   3    4
        #  |A    |
        #  | B   |  ===>       A    A    A        ===>            A
        #  |     |        ...   B    B    B  ...        ...   2    1
        #  +-----+
        #                      A    A    A
        #                       B    B    B
        
        >>> list( Board.distances_wrapped_on_torus(0, 0, 1, 1, 2, 2) )
        [(1, 1), (1, -1), (-1, -1), (-1, 1)]
        
        #
        #                  A A A 
        #  +--+             B B B
        #  |A |  ===>      A A A 
        #  | B|        ...  B B B ...
        #  +--+            A A A 
        #                   B B B
        """
        yield (yy-y),      (xx-x)
        yield (yy-y),      (xx-x-cols)
        yield (yy-y-rows), (xx-x-cols)
        yield (yy-y-rows), (xx-x)
        
    def newangles(self):
        """ Recalculate the direction of all birds. """

        # gather birds and their positions
        # --------------------------------
        # YES, this implementation is naïve with Θ(M*N) to only get birds :D
        # I'm not even sorry!
        # …okay, okay, maybe just a bit sorry
        # but even more lazy
        # TODO [kgdk] 28 mar 2015: fix
        birds = [(obj,x,y)
                 for (x,y,obj)
                 in chain(self.birds, self.blocks)
                ]

        # deathmatch! each bird agains every other
        perms = itertools.permutations(birds, 2)

        # gather results
        for (k, k_x, k_y), g in itertools.groupby(perms, key=itemgetter(0)):
            k.newangle(                                        # new angle for the bird
                itertools.chain.from_iterable(                 # is based on relative position
                    Board.distances_wrapped_on_torus(k_x, k_y, # of all of the other birds
                                                     b_x, b_y,
                                                     self.rows, self.cols
                                                    )
                    for _, (b, b_x, b_y) in g
                )
            )


class Block:
    def __init__(self):
        log.debug("NEW BLOCK")

    def disp_num(self):
        return 2

    def __str__(self):
        return '#'

    def step(self, x, y):
        log.debug("Block.step: return %d x %d", x, y)
        return x, y

    def newangle(self, other_birds):
        return 0

# ##############################################################################
# 🐦
# ##############################################################################
class Bird:
    bird_id = 0
    def __init__(self, direction):
        self.direction = radians_normalize(direction)
        # distance_fun is made separate for each bird so to allow some diversity,
        # e.g. birds who like crowds, lone birds, birds-sociopaths, etc.
        self.distance_fun = partial(f, a=1., b=1.)
        self.id = Bird.bird_id
        Bird.bird_id += 1
        # TODO [kgdk] 29 mar 2015: add "importance", so we could model diverse
        # popularity / influence each bird generates

    def disp_num(self):
        return 1

    def __str__(self):
        """ Print the bird as an arrow.
        This allows for some nicer debugging since we know the direction of a bird.
        >>> print(Bird(0))
        →
        >>> print(Bird(m.pi))
        ←
        >>> print(Bird(m.pi + m.pi * 0.123))
        ←
        >>> print(Bird(m.pi + m.pi * 0.123))
        ←
        >>> print(''.join(str(  Bird(m.pi * ang  )) for ang in [0, 0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75]))
        →↘↓↙←↖↑↗
        """
        pi  = m.pi
        pi2 = m.pi * 0.5
        pi4 = m.pi * 0.25
        pi8 = m.pi * 0.125
        direction = radians_normalize(self.direction + pi8)
        ranges = [
            (0*pi4, 1*pi4, '→' ),
            (1*pi4, 2*pi4, '↘' ),
            (2*pi4, 3*pi4, '↓' ),
            (3*pi4, 4*pi4, '↙' ),
            (4*pi4, 5*pi4, '←' ),
            (5*pi4, 6*pi4, '↖' ),
            (6*pi4, 7*pi4, '↑' ),
            (7*pi4, 8*pi4, '↗' )
        ]
        for r_from, r_to, res in ranges:
            if r_from <= direction < r_to:
                log.debug("for direction %.4f returning %s", self.direction, res)
                return res
        else:
            log.error("whoopsie, direction %.4f did not fell into any of the ranges. Mea culpa…  — kgadek", self.direction)
            raise ArithmeticError()

    def step(self, old_x, old_y):
        """ Return new position where the bird wants to be.
        
        >>> Bird(0).step(0,0)
        (0, 5)
        
        >>> Bird(m.pi).step(0,0)
        (0, -5)
        
        >>> Bird(m.pi / 2).step(0,0)
        (5, 0)
        """
        new_x = rand_round(old_x + V * m.sin(self.direction))
        new_y = rand_round(old_y + V * m.cos(self.direction))
        log.debug("old: (%d,%d) new: (%d,%d)", old_x, old_y, new_x, new_y)
        return new_x, new_y

    def newangle(self, other_birds: ':: (distance_x, distance_y)'):
        """ Calculate new angle basing on other birds.
        
        >>> b=Bird(0);    print(b.newangle(  []  ),      b)
        0.0 →
        
        >>> b=Bird(m.pi); print(b.newangle(  []  ),      b)
        3.141592653589793 ←
        
        >>> b=Bird(0);    print(b.newangle(  [(2,0)]  ), b)
        1.5707963267948966 ↓
        
        >>> b=Bird(0);    print(b.newangle(  [(-2,0)]  ), b)
        4.71238898038469 ↑
        
        >>> b=Bird(0);    print(b.newangle(  [(0,2)]  ), b)
        0.0 →
        
        >>> b=Bird(0);    print(b.newangle(  [(0,-2)]  ), b)
        3.141592653589793 ←
        """
        other_birds = list(other_birds)

        oldangle = self.direction
        influences = [ self.distance_fun( m.sqrt(dx**2 + dy**2) ) for dx, dy in other_birds ]
        sum_drows = sum( 1. * distance_x
                         for (distance_x, distance_y), influence
                         in chain(zip(other_birds, influences)))
        sum_dcols = sum( 1. * distance_y
                         for (distance_x, distance_y), influence
                         in chain(zip(other_birds, influences)))
        self.direction = radians_normalize(-m.atan2(sum_dcols, sum_drows) + m.pi/2)
        # TODO [kgdk] 29 mar 2015: make the change of direction a bit slower
        log.debug("bird %d old angle = %.4f new angle = %.4f", self.id, oldangle, self.direction)

        return self.direction


game = None

@route('/new/<rows:int>/<cols:int>/<birds:int>')
def mknew(rows,cols,birds):
    global game
    game = Board(rows,cols)
    for i in range(birds):
        game.add_random_bird()
    return str(game)

@route('/step')
def gamestep():
    global game
    if not game:
        game = Board(256,128)

        game.add_block(34,26)
        game.add_block(33,27)
        game.add_block(34,27)
        game.add_block(35,27)
        game.add_block(32,28)
        game.add_block(33,28)
        game.add_block(34,28)
        game.add_block(35,28)
        game.add_block(36,28)
        game.add_block(31,29)
        game.add_block(32,29)
        game.add_block(33,29)
        game.add_block(34,29)
        game.add_block(35,29)
        game.add_block(36,29)
        game.add_block(37,29)
        game.add_block(30,30)
        game.add_block(31,30)
        game.add_block(32,30)
        game.add_block(33,30)
        game.add_block(34,30)
        game.add_block(35,30)
        game.add_block(36,30)
        game.add_block(37,30)
        game.add_block(38,30)
        game.add_block(31,31)
        game.add_block(32,31)
        game.add_block(33,31)
        game.add_block(34,31)
        game.add_block(35,31)
        game.add_block(36,31)
        game.add_block(37,31)
        game.add_block(32,32)
        game.add_block(33,32)
        game.add_block(34,32)
        game.add_block(35,32)
        game.add_block(36,32)
        game.add_block(33,33)
        game.add_block(34,33)
        game.add_block(35,33)
        game.add_block(34,34)
        for i in range(30):
            game.add_random_bird()
        for i in range(6):
            game.add_random_block()

    game.step()

    if bottle.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        res = game.tojson()
        log.debug("JSON: %s", res)
        return res
    else:
        return str(game)



@route('/cors', method=['OPTIONS', 'GET'])
def lvambience():
    response.headers['Content-type'] = 'application/json'
    return '[1]'
	
@route('/<filepath:path>')
def server_static(filepath):
    pwd = Path('.') / 'page'
    return static_file(filepath, root=str(pwd.resolve()))

@route('/')
def default():
    return bottle.redirect("/index.html")
	
if __name__ == '__main__':
    import doctest
    doctest.testmod()
    apps = bottle.app()
    apps.run(host='localhost', port=8080)
	