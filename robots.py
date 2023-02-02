import numpy as np
from contextlib import contextmanager
from collections import deque
from time import time

from helpers import *

class RobotBoard:
    def __init__(self, size):
        self.size = size
        self.height, self.width = size
        self.h_walls = np.zeros((self.height+1, self.width), dtype = bool)
        self.v_walls = np.zeros((self.height, self.width+1), dtype = bool)
        self.h_walls[0,:] = True
        self.h_walls[-1,:] = True
        self.v_walls[:,0] = True
        self.v_walls[:,-1] = True

    def set_wall(self, pos, d, value = True):
        y,x = pos
        if d == LEFT:
            self.v_walls[y,x] = value
        if d == UP:
            self.h_walls[y,x] = value
        if d == RIGHT:
            self.v_walls[y,x+1] = value
        if d == DOWN:
            self.h_walls[y+1,x] = value

    def get_wall(self, pos, d):
        y,x = pos
        if d == LEFT:
            return self.v_walls[y,x]
        if d == UP:
            return self.h_walls[y,x]
        if d == RIGHT:
            return self.v_walls[y,x+1]
        if d == DOWN:
            return self.h_walls[y+1,x]

    @contextmanager
    def temporary_block(self, *positions):
        ori = [
            (
                tuple(self.h_walls[y:y+2,x]),
                tuple(self.v_walls[y,x:x+2])
            )
            for y,x in positions
        ]
        for y,x in positions:
            self.h_walls[y:y+2,x] = True
            self.v_walls[y,x:x+2] = True
        yield
        for (y,x),(h_ori,v_ori) in zip(positions, ori):
            self.h_walls[y:y+2,x] = h_ori
            self.v_walls[y,x:x+2] = v_ori

    def hit_wall_all(self, y0,x0): # LEFT, UP, RIGHT, DOWN
        res = []
        y,x = y0,x0
        while not self.v_walls[y,x]: x -= 1
        res.append((y,x))
        x = x0
        while not self.h_walls[y,x]: y -= 1
        res.append((y,x))
        y = y0
        while not self.v_walls[y,x+1]: x += 1
        res.append((y,x))
        x = x0
        while not self.h_walls[y+1,x]: y += 1
        res.append((y,x))
        y = y0
        return res
    def hit_wall(self, y,x, d):
        if d == LEFT:
            while not self.v_walls[y,x]: x -= 1
        if d == UP:
            while not self.h_walls[y,x]: y -= 1
        if d == RIGHT:
            while not self.v_walls[y,x+1]: x += 1
        if d == DOWN:
            while not self.h_walls[y+1,x]: y += 1
        return y,x
    
    def copy(self):
        res = RobotBoard(self.size)
        res.h_walls = np.array(self.h_walls)
        res.v_walls = np.array(self.v_walls)
        return res

    def search(self, ini):
        stack = [ini]
        visited = np.zeros(self.size, dtype = bool)
        while stack:
            pos = stack.pop()
            if visited[pos]: continue
            visited[pos] = True
            stack.extend(self.hit_wall_all(*pos))
        return visited

    def search2(self, ini1, ini2): # all possible constelations of two robots
        q = deque([(ini1, ini2)])
        visited = set()
        res = []
        t1 = time()
        precomputed = [[None for _ in range(self.width)] for _ in range(self.height)]
        for y in range(self.height):
            for x in range(self.width):
                precomputed[y][x] = self.hit_wall_all(y,x)
        t2 = time()
        #print("Precomputation: ",t2-t1)
        prep_time = 0
        indep_time = 0
        dep_time = 0
        while q:
            t1 = time()
            poss = q.popleft()
            if poss in visited: continue
            visited.add(poss)
            res.append(poss)
            pos1, pos2 = poss
            t2 = time()
            prep_time += t2-t1
            poss1h = precomputed[pos1[0]][pos1[1]]
            poss2h = precomputed[pos2[0]][pos2[1]]

            independent = True
            if pos1[0] == pos2[0]: # same row
                if pos1[1] > pos2[1]: # pos2 on the left
                    if poss1h[0][1] <= pos2[1]:
                        poss1h = list(poss1h)
                        poss2h = list(poss2h)
                        poss1h[0] = (pos2[0], pos2[1]+1)
                        poss2h[2] = (pos1[0], pos1[1]-1)
                        independent = False
                else: # pos2 on the right
                    if poss1h[2][1] >= pos2[1]:
                        poss1h = list(poss1h)
                        poss2h = list(poss2h)
                        poss1h[2] = (pos2[0], pos2[1]-1)
                        poss2h[0] = (pos1[0], pos1[1]+1)
                        independent = False
            elif pos1[1] == pos2[1]: # same column
                if pos1[0] > pos2[0]: # pos2 above
                    if poss1h[1][0] <= pos2[0]:
                        poss1h = list(poss1h)
                        poss2h = list(poss2h)
                        poss1h[1] = (pos2[0]+1, pos2[1])
                        poss2h[3] = (pos1[0]-1, pos1[1])
                        independent = False
                else: # pos2 below
                    if poss1h[3][0] >= pos2[0]:
                        poss1h = list(poss1h)
                        poss2h = list(poss2h)
                        poss1h[3] = (pos2[0]-1, pos2[1])
                        poss2h[1] = (pos1[0]+1, pos1[1])
                        independent = False
            q.extend((pos1h, pos2) for pos1h in poss1h)
            q.extend((pos1, pos2h) for pos2h in poss2h)
            if independent:
                indep_time += time() - t2
            else:
                dep_time += time() - t2
        #print("Preparation: ", prep_time)
        #print("Independent: ", indep_time)
        #print("Dependent: ", dep_time)
        return res        

class RobotsLevel:
    def __init__(self, board,
                 robot_positions, goal, robot_names):
        self.board = board
        self.size = board.size
        self.height = board.height
        self.width = board.width
        for y,x in robot_positions:
            assert 0 <= y < self.height and 0 <= x < self.width, f"Robot ({y+1},{x+1}) out of the plan"
        self.robot_positions = list(robot_positions)
        assert len(set(robot_positions)) == len(robot_positions), "2 robots on the same position"
        y,x = goal
        assert 0 <= y < self.height
        assert 0 <= x < self.width
        self.goal = goal
        self.robot_names = list(robot_names)

    @staticmethod
    def load_from_file(fname):
        with open(fname) as f:
            size = int(next(f))
            board = RobotBoard((size, size))
            robots_seen = set()
            robot_positions = []
            robot_names = []
            # load robots & goal
            for line in f:
                name, y, x = line.split()
                y = int(y)-1
                x = int(x)-1
                pos = (y,x)
                if name in robots_seen: break
                robots_seen.add(name)
                robot_positions.append(pos)
                robot_names.append(name)
            goal = pos
            # move goal robot at the first position
            index = robot_names.index(name)
            if index != 0:
                robot_names.insert(0,robot_names.pop(index))
                robot_positions.insert(0,robot_positions.pop(index))
            # load walls
            num_walls = int(next(f))
            real_num_walls = 0
            letter_to_direction = {'u': UP, 'd': DOWN, 'b': DOWN, 'l': LEFT, 'r': RIGHT}
            for line in f:
                y,x,letter = line.split()
                y = int(y)-1
                x = int(x)-1
                pos = (y,x)
                board.set_wall(pos, letter_to_direction[letter])
                real_num_walls += 1
            assert real_num_walls == num_walls, (real_num_walls, num_walls)

            return RobotsLevel(board, robot_positions, goal, robot_names)

    def export_to_file(self, fname):
        with open(fname, 'w') as f:
            self.export_to_stream(f)

    def export_to_stream(self, f):
        assert self.height == self.width, "Only square levels can be exported"
        # robots
        print(self.height, file = f)
        for name, (y,x) in zip(self.robot_names, self.robot_positions):
            print(name, y+1, x+1, file = f)
        # goal
        y,x = self.goal
        print(self.robot_names[0], y+1,x+1, file = f)
        # walls
        h_walls = self.board.h_walls[1:-1,:]
        v_walls = self.board.v_walls[:,1:-1]
        print(h_walls.sum() + v_walls.sum(), file = f)
        for y,x in positions_true(h_walls):
            print(y+1,x+1, 'd', file = f)
        for y,x in positions_true(v_walls):
            print(y+1,x+1, 'r', file = f)
