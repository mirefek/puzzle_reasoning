import os
from robots_enc import *

def extend_mask(mask0, board, conservative = False):
    mask = np.array(mask0)
    visited = set()
    stack = [
        (pos,op_direction[d])
        for pos in positions_true(mask0)
        for d in directions
        if not conservative or board.get_wall(pos,d) or mask[move_pos(pos,d)]
    ]
    while stack:
        pos,d = stack.pop()
        if (pos,d) in visited: continue
        visited.add((pos,d))
        if board.get_wall(pos,d): continue
        pos = move_pos(pos,d)
        mask[pos] = True
        stack.extend(
            (pos, op_direction[d2])
            for d2 in directions
            if board.get_wall(pos,d2) or mask[move_pos(pos,d2)]
        )
    return mask

def get_simple_cnt_invariant(level, debug = False):
    mask0 = np.zeros(level.size, dtype = bool)
    mask0[level.goal] = True
    masks = [extend_mask(mask0, level.board, conservative = True)]
    for _ in range(len(level.robot_names)-1):
        masks.append(extend_mask(masks[-1], level.board))

    if debug:
        for mask in masks:
            print(mask.astype(int))
            print()

    # check if the masks are working
    ini_robots = np.zeros(level.size, dtype = bool)
    for pos in level.robot_positions:
        ini_robots[pos] = True
    for i,mask in enumerate(masks):
        if np.sum(ini_robots & mask) > i:
            return None

    def invariant(state):
        return reduce_and(
            at_most(state.all_robots[masks[i]])[i]
            for i in range(3)
        )
    return invariant

def try_simple_cnt_invariants():
    datadir = "./robots_levels/"
    sufficient = 0
    insufficient = 0
    for fname in sorted(os.listdir(datadir)):
    #for fname in ["unsol_0032.rr"]:
        full_fname = os.path.join(datadir, fname)
        print(f"{fname}...", flush = True)
        level = RobotsLevel.load_from_file(full_fname)
        invariant = get_simple_cnt_invariant(level)
        if invariant is not None: sufficient += 1
        else: insufficient += 1
        if invariant is None:
            print(f"{fname}: Simple counting invariant failed", flush = True)
        elif check_invariant(level, invariant):
            print(f"{fname}: Simple counting invariant correct", flush = True)
        else: print(f"{fname}: ERROR: Simple counting invariant WRONG!", flush = True)

    print("Sufficient:", sufficient)
    print("Insufficient:", insufficient)

def inv0011(state):
    cond = neg(state.all_robots[4-1,14-1]) & state.all_robots[8-1,12-1]
    cond = cond & at_most(state.all_robots[3-1:9,14-1])[1]
    cond = cond & neg(
        state.all_robots[4-1,15-1] &
        reduce_or(
            state.all_robots[4-1,:13-1],
            state.all_robots[:3,10-1:11],
            state.all_robots[2-1,2-1:9],
        )
    )
    cond = cond & neg(
        state.all_robots[4-1,13-1] &
        reduce_or(state.all_robots[4-1,15-1:])
    )
    return cond

def inv0013(state):
    main0 = neg(state.all_robots[6-1,13-1])
    main_row0, main_row1 = at_most(state.all_robots[6-1,11-1:14])[:2]
    main_col0, main_col1 = at_most(state.all_robots[5-1:7,13-1])[:2]
    rows = [(
        list(state.all_robots[5-1,7-1:12]) +
        list(state.all_robots[5-1,14-1:])
    ), (
        list(state.all_robots[7-1,7-1:12]) +
        list(state.all_robots[7-1,14-1:]) +
        list(state.all_robots[8-1:,10-1])
    )]
    cols = [(
        list(state.all_robots[4-1:5,11-1]) +
        list(state.all_robots[7-1:,11-1])
    ), (
        list(state.all_robots[:5,12-1]) +
        list(state.all_robots[7-1:,12-1])
    ), (
        list(state.all_robots[:5,14-1]) +
        list(state.all_robots[7-1:12,14-1])
    )]
    rows1, rows2 = zip(*[
        at_most(row)[1:3]
        for row in rows
    ])
    cols1, cols2 = zip(*[
        at_most(col)[1:3]
        for col in cols
    ])
    return main0 & main_col1 & main_row1 & reduce_and(cols2) & reduce_and(rows2) & (
        main_row0 | reduce_and(cols1)
    ) & (
        main_col0 | reduce_and(rows1)
    )

if __name__ == "__main__":

    full_fname = "./robots_levels/unsol_0011.rr"
    level = RobotsLevel.load_from_file(full_fname)
    print("Level:", full_fname)
    check_invariant(level, inv0011)

    try_simple_cnt_invariants()
