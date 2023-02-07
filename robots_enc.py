from robots import *
from formula import *
from state_enc import check_invariant, check_init_move, check_limited_solvable, GameState

def row_move_right(state1, state2, walls):
    extra1 = [x & neg(y) for x,y in zip(state1, state2)]
    extra2 = [neg(x) & y for x,y in zip(state1, state2)]
    success = reduce_and( # check wall behind the path
        neg(ex) | w1 | w2
        for ex, w1, w2 in zip(extra2[:-1], walls, state2[1:])
    )
    path1, s = one_hot_to_rev_unary(extra1)
    success = success & s
    path2, s = one_hot_to_rev_unary(extra2)
    success = success & s
    success = success & reduce_and( # path starts before it ends
        x1 | neg(x2)
        for x1,x2 in zip(path1, path2)
    )
    path = [x1 & neg(x2) for x1, x2 in zip(path1, path2)]
    success = success & reduce_and( # no obstacle on the path
        neg(x) | (neg(w1) & neg(w2))
        for x,w1,w2 in zip(path, walls, state1[1:])
    )
    return success #, path1, path2, path

def row_move(state1, state2, walls):
    assert len(state2) == len(state1)
    assert len(walls) == len(state1)-1
    rstate1 = list(reversed(state1))
    rstate2 = list(reversed(state2))
    rwalls = list(reversed(walls))
    return row_move_right(state1, state2, walls) | row_move_right(rstate1, rstate2, rwalls)

def move_horizontal(state1, state2, walls):
    move_in_row = [
        row_move(s1,s2,w)
        for s1,s2,w in zip(state1, state2, walls)
    ]
    return exactly_one(move_in_row) & reduce_and(
        move | dep_equal(s1, s2)
        for move, s1, s2 in zip(move_in_row, state1, state2)
    )

class RobotState(GameState, level = RobotsLevel):
    def initialize(self, level):
        self.level = level
        self.all_robots = np.empty(level.size, dtype = self.np_type)
        self.main_robot = np.empty_like(self.all_robots)
        for y in range(level.height):
            for x in range(level.width):
                self.all_robots[y,x] = self.new(BoolVar)
                self.main_robot[y,x] = self.new(BoolVar)

        # calculate is_correct
        x = count_exact(self.all_robots.flat)[len(level.robot_names)]
        x = x & count_exact(self.main_robot.flat)[1]
        x = x & reduce_and(
            neg(m) | a
            for m,a in zip(self.main_robot.flat, self.all_robots.flat)
        )
        self.is_correct = x

        # initial and goal conditions
        self.is_init = self.main_robot[level.robot_positions[0]] & reduce_and(
            self.all_robots[pos]
            for pos in level.robot_positions
        )
        self.is_goal = self.main_robot[level.goal]

    def transition(self, state2):
        h_walls = self.level.board.h_walls[1:-1,:]
        v_walls = self.level.board.v_walls[:,1:-1]

        x = (
            move_horizontal(self.all_robots, state2.all_robots, v_walls)  |
            move_horizontal(self.all_robots.T, state2.all_robots.T, h_walls.T)
        )
        # move main pointer only with a robot
        x = x & reduce_and(
            neg(a1) | neg(a2) | m1.equals(m2)
            for m1, a1, m2, a2 in zip(self.main_robot.flat, self.all_robots.flat,
                                      state2.main_robot.flat, state2.all_robots.flat)
        )
        return x        

    def to_str(self):
        ascii_plan = np.full([2*self.level.height+1, 2*self.level.width+1], '..')
        ascii_plan[::2,::2] = "+"
        ascii_h_walls = np.array(["  ", "--"])[self.level.board.h_walls.astype(int)]
        ascii_v_walls = np.array([" ", "|"])[self.level.board.v_walls.astype(int)]
        ascii_plan[::2,1::2] = ascii_h_walls
        ascii_plan[1::2,::2] = ascii_v_walls
        ascii_robots = np.array(["  ", "()", "{}", "[]"])[2*self.main_robot + self.all_robots]
        ascii_plan[1::2,1::2] = ascii_robots
        return '\n'.join(
            ''.join(line)
            for line in ascii_plan
        )

def check_example_invariant():

    fname = "robots_levels/unsol_0002.rr"
    level = RobotsLevel.load_from_file(fname)
    masks = [
        np.zeros(level.size, dtype = bool)
        for _ in range(3)
    ]
    masks[0][4,2] = True
    masks[1][3:6,2] = True
    masks[2][3:6,2] = True
    masks[2][3,:] = True
    masks[2][5,:] = True
    masks[2][0:4,5] = True
    masks[2][1:6,9] = True
    def invariant(state):
        return reduce_and(
            at_most(state.all_robots[masks[i]])[i]
            for i in range(3)
        )

    check_invariant(level, invariant)

def check_example_transition():

    fname = "./robots_levels/unsol_0002.rr"
    level = RobotsLevel.load_from_file(fname)
    check_init_move(level)


def check_example_solvable():
    
    fname = "./robots_levels/0.rr"
    level = RobotsLevel.load_from_file(fname)

    check_limited_solvable(level, 6, states_in_row = 1)

if __name__ == "__main__":

    check_example_transition()
    check_example_invariant()
    check_example_solvable()
