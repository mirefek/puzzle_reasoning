from rush_hour import RushHourLevel
from helpers import *
from formula import *
from state_enc import check_invariant, check_init_moves, check_limited_solvable, GameState
import numpy as np
from solver import solve

class CarState(BoolObject):
    def initialize(self, plan_size, car_size, sum_before, sum_after):

        self.plan_size = plan_size
        self.car_size = car_size
        # print(f"CarState({plan_size}, {car_size}, {sum_before}, {sum_after})")

        first_pos = [
            self.new(BoolVar)
            for _ in range(plan_size - sum_before - car_size - sum_after + 1)
        ]
        self.first_pos = [False]*sum_before + first_pos + [False]*(car_size + sum_after-1)

        start_before, self.car_correct = one_hot_to_rev_unary(first_pos)
        end_after, _ = one_hot_to_rev_unary(reversed(first_pos))
        end_after.reverse()
        self.start_before = [False]*sum_before + start_before + [True]*(car_size + sum_after)
        self.end_after = [True]*(sum_before + car_size) + end_after + [False]*(sum_after)

        # print("first_pos", len(first_pos))
        # print("start_before", len(start_before))
        # print("end_after", len(end_after))
        # print("self.first_pos", len(self.first_pos))
        # print("self.start_before", len(self.start_before))
        # print("self.end_after", len(self.end_after))

        assert len(self.first_pos) == plan_size
        assert len(self.start_before) == plan_size
        assert len(self.end_after) == plan_size
        self.all_pos = [a & b for a,b in zip(self.start_before, self.end_after)]
        self.start_after = [neg(x) for x in self.start_before]
        self.end_before = [neg(x) for x in self.end_after]

class RushState(GameState, level = RushHourLevel):
    def initialize(self, level):
        self.level = level
        self.size = level.size
        self.height, self.width = self.size

        self.all_cars_list = []
        self.is_correct = True
        self.h_cars = [
            self._init_row(cars_in_row, self.width, walls)
            for cars_in_row, walls in zip(level.h_cars, level.walls)
        ]
        self.v_cars = [
            self._init_row(cars_in_row, self.height, walls)
            for cars_in_row, walls in zip(level.v_cars, level.walls.T)
        ]
        self.cars = [self.h_cars, self.v_cars]
        self.letter_to_car = {
            letter : self.cars[hv][i][j]
            for letter, (hv,i,j) in level.letter_to_car_index.items()
        }

        self.occupied_h = np.array([
            self._get_occupied(cars, self.width)
            for cars in self.h_cars
        ], dtype = self.np_type)
        self.occupied_v = np.transpose(np.array([
            self._get_occupied(cars, self.height)
            for cars in self.v_cars
        ], dtype = self.np_type))
        self.is_correct = self.is_correct & reduce_and(
            neg(x) | neg(y)
            for x,y in zip(self.occupied_h.flat, self.occupied_v.flat)
        )
        self.occupied = self.occupied_h | self.occupied_v

        self.is_init = reduce_and([
            [
                car_state.first_pos[car_ini[0]]
                for car_state, car_ini in zip(row_states, ini_states)
            ]
            for row_states, ini_states in zip(self.h_cars+self.v_cars, level.h_cars+level.v_cars)
        ])
        (hv,i,j),pos = level.goal
        self.is_goal = self.cars[hv][i][j].first_pos[pos]

    def transition(self, other):
        # exactly one car moves
        row_move = [
            neg(dep_equal(
                [car1.first_pos for car1 in row1],
                [car2.first_pos for car2 in row2],
            ))
            for row1, row2 in zip(self.h_cars + self.v_cars, other.h_cars + other.v_cars)
        ]
        one_row_moves = count_exact(row_move)[1]

        # it doesn't jump over another car
        occupied_h = np.array([
            self._get_shift_occupied(cars1, cars2, self.width)
            for cars1, cars2 in zip(self.h_cars, other.h_cars)
        ], dtype = self.np_type)
        occupied_v = np.transpose(np.array([
            self._get_shift_occupied(cars1, cars2, self.height)
            for cars1, cars2 in zip(self.v_cars, other.v_cars)
        ], dtype = self.np_type))
        no_jump = self.is_correct & reduce_and(
            neg(x) | neg(y)
            for x,y in zip(occupied_h.flat, occupied_v.flat)
        )

        return one_row_moves & no_jump

    def to_str(self):
        ascii_plan = np.array(['.', 'x'])[self.level.walls.astype(int)]
        for letter,(hv,i,j) in self.level.letter_to_car_index.items():
            car = self.cars[hv][i][j]
            if hv == 0:
                y = i
                for x,b in enumerate(car.all_pos):
                    if b: ascii_plan[y,x] = letter
            else:
                x = i
                for y,b in enumerate(car.all_pos):
                    if b: ascii_plan[y,x] = letter
        return '\n'.join(
            ''.join(line)
            for line in ascii_plan
        )

    def _init_row(self, cars, dim, walls):
        wall_ids = [i for i,x in enumerate(walls) if x]
        segments = [
            (w1+1,w2)
            for w1,w2 in zip([-1]+wall_ids, wall_ids+[dim])
        ]
        # print("wall_ids", wall_ids)
        cars_i = 0
        res = []
        for start, end in segments:
            if cars_i == len(cars) or cars[cars_i][0] >= end: continue
            current_cars = []
            while cars_i < len(cars) and cars[cars_i][1] <= end:
                current_cars.append(cars[cars_i])
                cars_i += 1
            res.extend(self._init_segment(current_cars, dim, start, end))
        return res

    def _init_segment(self, cars, dim, start, end):
        if not cars: return []
        sizes = np.array([x2-x1 for x1,x2 in cars])
        # print("init_segment", sizes, dim, start, end)
        cum_sizes = np.cumsum(sizes)
        sum_sizes = cum_sizes[-1]
        sums_before = np.concatenate([[0], cum_sizes[:-1]])
        sums_after = sum_sizes - sizes - sums_before
        res = [
            self.new(CarState, dim, size, sum_before + start, sum_after + (dim-end))
            for size, sum_before, sum_after in zip(sizes, sums_before, sums_after)
        ]
        self.all_cars_list.extend(res)

        row_correct = reduce_and(
            car.car_correct for car in res
        )
        row_correct = row_correct & reduce_and(
            [x | y for x,y in zip(car1.end_before, car2.start_after)]
            for car1, car2 in zip(res[:-1], res[1:])
        )
        self.is_correct = self.is_correct & row_correct

        return res

    def _get_occupied(self, cars, dim):
        res = [False]*dim
        for car in cars:
            for i,x in enumerate(car.all_pos):
                res[i] = res[i] | x
        return res
    def _get_shift_occupied(self, cars1, cars2, dim):
        res = [False]*dim
        for car1, car2 in zip(cars1, cars2):
            for i in range(dim):
                res[i] = res[i] | (
                    (car1.start_before[i] | car2.start_before[i]) &
                    (car1.end_after[i] | car2.end_after[i])
                )
        return res


def check_example_transition():

    fname = "./rush_unsolvable.txt"
    with open(fname) as f:
        level_lines = list(f)
    level = RushHourLevel.from_line(level_lines[0])
    check_init_moves(level)

def check_example_invariants():

    num_levels = 3
    fname = "./rush_unsolvable.txt"
    with open(fname) as f:
        level_lines = list(f)

    invariants = [
        lambda cars: reduce_and(
            cars['J'].end_before[5],
            cars['A'].end_before[4],
            cars['C'].start_after[1],
            cars['I'].start_after[1],
            cars['B'].end_before[4],
        ),
        lambda cars: reduce_and(
            cars['A'].end_before[5],
            cars['B'].start_after[0] | cars['I'].start_after[2],
            cars['I'].start_after[2] | cars['A'].end_before[4] | cars['B'].start_after[3],
        ),
        lambda cars: reduce_and(
            cars['A'].end_before[4],
            cars['F'].start_after[1],
            implies(
                cars['E'].start_before[1],
                cars['H'].start_before[1],
            )
        ),
        lambda cars: reduce_and(
            cars['A'].end_before[5],
            implies(
                cars['E'].start_before[1],
                cars['K'].start_before[1],
            ),
            implies(
                cars['L'].start_after[2],
                reduce_and(
                    [a | b for a,b in zip(cars['A'].start_before, cars['B'].start_after)],
                )
            ),
            implies(
                cars['B'].start_before[0],
                cars['J'].start_after[2],
            )
        ),
        lambda cars: reduce_and(
            cars['A'].end_before[5],
            implies(
                cars['C'].start_before[2],
                cars['A'].start_before[1],
            )
        ),
        lambda cars: cars['A'].start_before[2] | cars['G'].end_after[5],
        lambda cars: cars['A'].start_before[2] | cars['G'].end_after[5],
        lambda cars: reduce_and(
            cars['A'].end_before[5],
            cars['I'].end_before[5],
            implies(cars['A'].start_after[1], cars['K'].start_after[2]),
            implies(
                cars['A'].start_after[0], cars['E'].start_before[2],
                cars['B'].start_after[2],
            ),
            implies(cars['A'].start_before[1], cars['I'].start_before[0]),
            implies(cars['E'].start_before[0], cars['J'].end_before[5]),
        ),
        lambda cars: reduce_and(
            cars['A'].end_before[5],
            cars['G'].start_after[0],
            cars['M'].start_after[0],
            implies(
                cars['A'].start_before[1], cars['E'].end_after[5],
                cars['K'].start_before[0]
            ),
            implies(
                cars['F'].start_before[0], cars['K'].start_before[3],
            ),
            implies(
                cars['G'].start_before[1],
                (cars['F'].start_after[2] & cars['M'].start_before[1]),
            ),
        ),
        lambda cars: reduce_and(
            cars['A'].end_before[4],
            implies(
                cars['B'].start_before[2], cars['A'].start_after[0],
                cars['K'].start_after[2],
            ),
        ),
        lambda cars: reduce_and(
            cars['A'].end_before[5],
            cars['E'].start_after[0],
            implies(cars['A'].end_after[4], cars['E'].end_after[5]),
        )
    ]

    for level_i, (line, invariant) in enumerate(zip(level_lines, invariants)):
        level = RushHourLevel.from_line(level_lines[level_i])
        print(f"Checking invariant for unsolvable level {level_i}")
        check_invariant(level, lambda state: invariant(state.letter_to_car))

def check_example_solvable():
    
    fname = "./rush_solvable.txt"
    with open(fname) as f:
        level_lines = list(f)
    level = RushHourLevel.from_line(level_lines[0])

    check_limited_solvable(level, 35, states_in_row = 8)

if __name__ == "__main__":

    check_example_solvable()
    check_example_transition()
    check_example_invariants()
