import os
from soko_enc import *
from helpers import *

def boxes_state(state, *boxes, sk = None, nsk = None, vals = None, comp_block = None):
    if sk is not None or nsk is not None:
        assert not (sk is None and nsk is None)
        if sk is None:
            sk = nsk
            sk_negated = True
        else:
            sk_negated = False
        available = ~state.level.walls
        for box in boxes:
            available[box] = False
        if comp_block:
            if isinstance(comp_block[0], numbers.Integral):
                comp_block = [comp_block]
            for pos in comp_block:
                available[pos] = False
        sk = component2d(available, *sk)
        cond_sk = reduce_or(state.sk[sk])
        if sk_negated: cond_sk = neg(cond_sk)
    else:
        cond_sk = True
    cond_boxes = reduce_and(
        state.boxes[box]
        for box in boxes
    )
    return cond_sk & cond_boxes

def simple_deadlocks(state, vals = None):
    reachable = np.zeros_like(state.level.storages)
    stack = list(positions_true(state.level.storages))
    while stack:
        pos = stack.pop()
        if reachable[pos]: continue
        reachable[pos] = True
        for d in directions:
            pos2 = move_pos(pos, d)
            if not state.level.available_pos(pos2): continue
            pos3 = move_pos(pos2, d)
            if not state.level.available_pos(pos3): continue
            stack.append(pos2)
    unreachable = ~(state.level.walls | reachable)
    cond_single = reduce_or(
        state.boxes[unreachable]
    )
    cond_squares = False
    end_resolved = state.level.walls | state.level.storages
    for y in range(state.level.height-1):
        for x in range(state.level.width-1):
            if unreachable[y:y+2,x:x+2].any(): continue
            if end_resolved[y:y+2,x:x+2].all(): continue
            sq_walls = state.level.walls[y:y+2,x:x+2]
            if sq_walls.sum() > 2: continue
            if sq_walls.sum() == 2 and sq_walls[0,0] == sq_walls[1,1]: continue
            cur_square = reduce_and(
                state.boxes[y:y+2,x:x+2][~sq_walls]
            )
            cond_squares = cond_squares | cur_square
    return cond_single | cond_squares

def cave_right_upper(state):
    left =  (state.boxes[7,7] & neg(state.sk[7,8])) | state.boxes[7,8]
    left = left & state.boxes[8,8]
    left = left & neg(state.sk[7,9]) & neg(state.sk[8,9])
    blocked = left & state.boxes[7,9]
    left = left | state.boxes[7,9]
    right = state.boxes[9,11] & state.boxes[8,12] & neg(state.sk[8,11])
    right = (right | state.boxes[8,11]) & state.boxes[7,12]
    right = (right & neg(state.sk[7,11])) | state.boxes[7,11]
    right = right | (
        boxes_state(
            state,
            (9,11), (9,12),
            nsk = (8,12),
            comp_block = (7,10),
        ) & (
            state.boxes[7,12] | state.boxes[8,12]
        )
    )
    right = right | boxes_state(
        state,
        (8,11), (8,12), (9,12),
        nsk = (8,13),
        comp_block = (7,10),
    )
    return reduce_or(
        left & right & neg(state.sk[7,10]),
        left & state.boxes[7,10],
        right & state.boxes[7,10],
        blocked,
    )

def cave_right_bottom(state):
    left = reduce_and(state.boxes[9,7:9])
    left = left | reduce_and(
        state.boxes[8,7:9],
        reduce_or(state.boxes[9,7:9]),
        neg(reduce_or(state.sk[9,7:9])),
    )
    right = reduce_and(state.boxes[9,11:13])
    right = right | reduce_and(
        state.boxes[8,11], state.boxes[9,12],
        neg(state.sk[9,11]),
    )
    right = right | boxes_state(
        state,
        (8,11), (8,12), (7,12),
        nsk = (9,12),
        comp_block = [(10,11),(10,12)],
    )
    right = right | boxes_state(
        state,
        (9,11), (8,12), (7,12),
        nsk = (9,12),
        comp_block = [(10,11),(10,12)],
    )
    mask = np.zeros(state.level.size, dtype = bool)
    mask[7:10,11:14] = True
    mask[7,11] = False
    right = right | reduce_and(
        neg(at_most(state.boxes[mask])[1]),
        neg(reduce_or(state.sk[mask])),
        reduce_or(
            state.boxes[7,11],
            state.boxes[7,10] & neg(state.sk[7,11]),
            state.boxes[7,9] & neg(state.sk[7,10]) & neg(state.sk[7,11]),
        )
    )
    return reduce_and(
        left, right, neg(reduce_or(state.sk[10,7:13]))
    )

def cave_right(state):
    box_count_mask = np.zeros(state.level.size, dtype = bool)
    box_count_mask[7:11,7:14] = True
    box_count_mask &= ~state.level.walls
    box_count_mask[7:9,7] = False
    nsk_mask = np.array(box_count_mask, dtype = bool)
    box_count_mask[7:9,8] = False
    cnt = at_most(state.boxes[box_count_mask])
    cave_start = reduce_and(
        state.boxes[7,7] | state.boxes[7,8],
        state.boxes[8,7] | state.boxes[8,8],
        neg(cnt[3]) | (neg(cnt[2]) & state.boxes[8,7] & state.boxes[8,8]),
        neg(reduce_or(state.sk[nsk_mask])),
    )
    cave_end = reduce_or(
        boxes_state(state, (7,12), (8,12), (9,12), nsk = (8,13)),
        boxes_state(state, (7,11), (8,12), (9,12), nsk = (8,13)),
    )
    return cave_start | cave_right_upper(state) | cave_right_bottom(state) | cave_end

def cave_left_up(state):
    res = state.boxes[6,3]
    for i in range(5,1,-1):
        res = res & state.boxes[i,2] & neg(state.sk[i,3])
        if i > 2: res = res | state.boxes[i,3]
    return neg(reduce_or(state.sk[1,2:4])) & (res | (
        state.boxes[3,2] & state.boxes[2,3] & neg(state.sk[2,2])
    ))

def cave_mid_up(state):
    return False
    # TODO

def specific_deadlocks(state, vals):
    return reduce_or(
        reduce_and(
            reduce_or(state.boxes[2:4,2]),
            reduce_or(state.boxes[2:4,3]),
            neg(reduce_or(state.sk[1:3,2:4])),
        ),
        cave_right(state),
        cave_left_up(state),
    )

def inv26(state, vals = None):
    ini_boxes = np.array(state.level.boxes)
    ini_boxes[3:5,8] = False
    ini_boxes = positions_true(ini_boxes)
    sk = state.level.storekeeper
    ini = reduce_or(
        boxes_state(state, (3,8), (4,8), *ini_boxes, sk = sk),
        boxes_state(state, (4,7), *ini_boxes, sk = sk, vals = vals),
        boxes_state(state, (4,6), *ini_boxes, sk = sk),
    )
    mask = np.zeros_like(state.level.boxes)
    mask[:,:6] = True
    mask[7:,:] = True
    mask &= ~state.level.walls
    cond = neg(at_most(state.boxes[mask])[11])
    mask[7:,7:] = False
    cond = cond & neg(at_most(state.boxes[mask])[6])
    cond = cond | simple_deadlocks(state, vals) | ini | specific_deadlocks(state, vals)
    return cond
    
if __name__ == "__main__":

    full_fname = "./soko_unsolvable.xsb"
    levels = SokoLevel.all_from_file(full_fname)
    level = levels[0]
    print("Level:", full_fname)
    check_invariant(level, inv26, debug = True)
    print("This invariant is not finished yet, it is expected that it is not working.")
