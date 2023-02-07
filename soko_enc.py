from sokoban import SokoLevel
from helpers import *
from formula import *
from state_enc import check_invariant, check_init_move, GameState
import numpy as np

def row_move(boxes1, boxes2, storekeeper1, storekeeper2):
    size = len(boxes1)
    assert len(boxes2) == size
    assert len(storekeeper1) == size
    assert len(storekeeper2) == size
    equal_squares = [
        dep_equal((b1,sk1), (b2,sk2))
        for b1, b2, sk1, sk2 in zip(boxes1, boxes2, storekeeper1, storekeeper2)
    ]
    equal_ini = [True]
    for x in equal_squares:
        equal_ini.append(equal_ini[-1] & x)
    equal_term = [True]
    for x in reversed(equal_squares):
        equal_term.append(equal_term[-1] & x)
    equal_term.reverse()
    templates_simple = [
        ([True, False], [False, False], [False, True], [False, False]),
        ([False, True], [False, False], [True, False], [False, False]),
    ]
    templates_push = [
        ([True, False, False], [False, True, False],
         [False, True, False], [False, False, True]),
        ([False, False, True], [False, True, False],
         [False, True, False], [True, False, False]),
    ]
    simple_move = reduce_or(
        reduce_or(
            dep_equal((
                storekeeper1[i:i+2], boxes1[i:i+2],
                storekeeper2[i:i+2], boxes2[i:i+2],
            ), template)
            for template in templates_simple
        ) & equal_ini[i] & equal_term[i+2]
        for i in range(size-1)
    )
    push_move = reduce_or(
        reduce_or(
            dep_equal((
                storekeeper1[i:i+3], boxes1[i:i+3],
                storekeeper2[i:i+3], boxes2[i:i+3],
            ), template)
            for template in templates_push
        ) & equal_ini[i] & equal_term[i+3]
        for i in range(size-2)
    )
    return (simple_move | push_move), equal_ini[-1]

def move_horizontal(boxes1, boxes2, storekeeper1, storekeeper2):
    move_in_row, equal_lines = zip(*[
        row_move(b1,b2,sk1,sk2)
        for b1,b2,sk1,sk2 in zip(boxes1, boxes2, storekeeper1, storekeeper2)
    ])
    return exactly_one(move_in_row) & reduce_and(
        move | eq
        for move, eq in zip(move_in_row, equal_lines)
    )

class SokoState(GameState, level = SokoLevel):
    def initialize(self, level):
        self.level = level
        self.sk = np.empty(level.size, dtype = self.np_type)
        self.boxes = np.empty(level.size, dtype = self.np_type)
        for y in range(level.height):
            for x in range(level.width):
                if self.level.walls[y,x]:
                    self.sk[y,x] = False
                    self.boxes[y,x] = False
                else:
                    self.sk[y,x] = self.new(BoolVar)
                    self.boxes[y,x] = self.new(BoolVar)

        # calculate is_correct
        x = count_exact(self.sk.flat)[1]
        x = x & count_exact(self.boxes.flat)[level.num_boxes]
        x = x & reduce_and(
            neg(sk) | neg(box)
            for sk, box in zip(self.sk.flat, self.boxes.flat)
        )
        self.is_correct = x

        # initial and goal conditions
        self.is_init = self.sk[level.storekeeper] & dep_equal(self.boxes, level.boxes)
        self.is_goal = dep_equal(self.boxes, level.storages)

    def transition(self, other):
        return (
            move_horizontal(self.boxes, other.boxes, self.sk, other.sk) |
            move_horizontal(self.boxes.T, other.boxes.T, self.sk.T, other.sk.T)
        )

    def to_str(self):
        ascii_plan = np.array([' ', '$', '@', '!', '#'])[
            4*self.level.walls + 2*self.sk + self.boxes
        ]
        return '\n'.join(
            ''.join(line)
            for line in ascii_plan
        )

def check_example_invariant():

    fname = "./soko_unsolvable.xsb"
    levels = SokoLevel.all_from_file(fname)
    level = levels[1]
    def invariant(state):
        return True

    check_invariant(level, invariant)

def check_example_transition():

    fname = "./soko_unsolvable.xsb"
    levels = SokoLevel.all_from_file(fname)
    level = levels[1]
    check_init_move(level)

if __name__ == "__main__":
    check_example_transition()
    check_example_invariant()
