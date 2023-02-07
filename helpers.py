import numpy as np
import numbers

LEFT = 0
UP = 1
RIGHT = 2
DOWN = 3
directions = [LEFT, UP, RIGHT, DOWN]
op_direction = [RIGHT, DOWN, LEFT, UP]

def np_all_positions(shape):
    return np.moveaxis(np.indices(shape), 0, -1)
def positions_true(a):
    return tuple(map(tuple, np_all_positions(a.shape)[a]))

def move_pos(pos,d):
    y,x = pos
    if d == LEFT: return (y,x-1)
    elif d == UP: return (y-1,x)
    elif d == RIGHT: return (y,x+1)
    elif d == DOWN: return (y+1,x)

def is_correct_pos(pos, size):
    y,x = pos
    height, width = size
    return 0 <= y < height and 0 <= x < width

def component2d(a, *ini):
    if isinstance(ini[0], numbers.Integral): stack = [ini]
    else: stack = list(ini)
    res = np.zeros_like(a)
    while stack:
        pos = stack.pop()
        if not is_correct_pos(pos, a.shape): continue
        if not a[pos]: continue
        if res[pos]: continue
        res[pos] = True
        stack.extend([
            move_pos(pos, d)
            for d in directions
        ])
    return res

def print_vcenter(*args, **kwargs): #
    if not args:
        print()
        return
    args = [str(arg).split('\n') for arg in args]
    for arg in args:
        if len(arg) > 1 and not arg[1]:
            arg.pop()
        elif not arg:
            arg.append('')
        size = max(len(line) for line in arg)
        for i,line in enumerate(arg):
            if len(line) < size:
                arg[i] = line+' '*(size-len(line))

    num_lines = max(len(arg) for arg in args)
    for i in range(len(args)):
        to_add = num_lines - len(args[i])
        to_add_top = to_add//2
        to_add_bot = to_add - to_add_top
        spaces = ' '*len(args[i][0])
        args[i] = to_add_top*[spaces] + args[i] + to_add_bot*[spaces]

    for line in zip(*args):
        print(*line, **kwargs)
