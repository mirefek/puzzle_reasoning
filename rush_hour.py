import numpy as np
from collections import defaultdict

class RushHourLevel:
    def __init__(self, walls, h_cars, v_cars, goal, letter_to_car_index):
        self.size = walls.shape
        self.height, self.width = self.size
        self.walls = walls
        self.h_cars = h_cars
        self.v_cars = v_cars
        self.cars = [h_cars, v_cars]
        self.letter_to_car_index = letter_to_car_index
        self.goal = goal
        assert len(h_cars) == self.height
        assert len(v_cars) == self.width
        for (cars, dim) in ((h_cars, self.width), (v_cars, self.height)):
            for cars_in_row in cars:
                if not cars_in_row: continue
                assert all(0 <= x1 < x2 <= dim for x1,x2 in cars_in_row)
                assert all(x2a <= x1b for (_,x2a),(x1b,_) in zip(cars_in_row[:-1], cars_in_row[1:]))

    @staticmethod
    def from_line(level_string):

        level_string = level_string.strip()

        cars = defaultdict(list)
        walls_list = []
        for i,c in enumerate(level_string):
            if c == '.' or c == 'o': continue
            if c == 'x': walls_list.append(i)
            else: cars[c].append(i)

        # detect width
        for vc,car in cars.items():
            if len(car) < 2: raise Exception(f"Car '{vc}' contains just a single item")
            if car[1] - car[0] > 1:
                width = car[1] - car[0]
                break
        else:
            raise Exception("No vertical car -> couldn't detect level width")
        if len(level_string) % width != 0:
            raise Exception(
                f"Cannot decompose size {len(level_string)} into {width} x ? (got from car '{vc}')")
        height = len(level_string) // width
        walls = np.zeros([height, width], dtype = bool)
        for x in walls_list:
            walls[x // width, x % width] = True

        letter_to_car_index = dict()
        h_cars = [[] for _ in range(height)]
        v_cars = [[] for _ in range(width)]
        for c, car in cars.items():
            stride = car[1] - car[0]
            if stride != 1 and stride != width:
                raise Exception(f"Car '{c}' doesn't have stride 1 nor {width} (got from car '{vc}')")
            if not all((b-a == stride for a,b in zip(car[1:], car[2:]))):
                raise Exception(f"Car '{c}' has irregular stride")
            if stride == 1:
                y = car[0] // width
                if y != car[-1] // width:
                    raise Exception(f"Horizontal car '{c}' is crossing a line (line width = {width} by car '{vc}')")
                x1 = car[0] % width
                x2 = car[-1] % width+1
                letter_to_car_index[c] = (0, y, len(h_cars[y]))
                h_cars[y].append((x1,x2))
            else:
                x = car[0] % width
                y1 = car[0] // width
                y2 = car[-1] // width+1
                letter_to_car_index[c] = (1, x, len(v_cars[x]))
                v_cars[x].append((y1,y2))

        cars = [h_cars, v_cars]
        if 'A' not in letter_to_car_index:
            raise Exception("Warning: There is no main car 'A' in the level")
        goal_index = letter_to_car_index['A']
        hv, i,j = goal_index
        assert len(cars[hv][i]) == j+1
        goal_car_x1, goal_car_x2 = cars[hv][i][j]
        goal_car_size = goal_car_x2 - goal_car_x1
        if hv == 0: # horizontal
            goal_pos = width - goal_car_size
        else:
            goal_pos = height - goal_car_size

        goal = goal_index, goal_pos

        return RushHourLevel(walls, h_cars, v_cars, goal, letter_to_car_index)
