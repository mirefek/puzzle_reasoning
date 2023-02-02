import numpy as np

class SokoLevel:
    def __init__(self, walls, storages, boxes, storekeeper):
        self.walls = np.array(walls, dtype = bool)
        self.storages = np.array(storages, dtype = bool)
        self.boxes = np.array(boxes, dtype = bool)
        self.size = self.walls.shape
        self.num_boxes = np.sum(boxes)
        assert self.walls.shape == self.size
        assert self.walls.shape == self.size
        assert np.sum(storages) == self.num_boxes
        assert not (self.walls & self.boxes).any()
        assert not (self.walls & self.storages).any()
        assert (self.storages != self.boxes).any()

        self.storekeeper = tuple(storekeeper)
        self.height, self.width = self.size
        assert 0 <= self.storekeeper[0] < self.height
        assert 0 <= self.storekeeper[1] < self.width
        # positions are indexed from 1 (to simplify wall check)
        assert not self.boxes[self.storekeeper] and not self.walls[self.storekeeper]

    @staticmethod
    def from_lines(lines):
        char_d = {
            ' ': (0,0,0,0),
            '#': (1,0,0,0),
            '.': (0,1,0,0),
            '$': (0,0,1,0),
            '*': (0,1,1,0),
            '@': (0,0,0,1),
            '+': (0,1,0,1),
        }
        m = max(len(line) for line in lines)
        lines = [
            line+(' '*(m-len(line)))
            for line in lines
        ]
        np_level = np.array([
            [char_d[x] for x in line]
            for line in lines
        ])
        walls, storages, boxes, storekeeper = np.transpose(np_level, (2,0,1))
        assert np.sum(storekeeper) == 1
        storekeeper = np.unravel_index(np.argmax(storekeeper), storekeeper.shape)
        return SokoLevel(walls, storages, boxes, storekeeper)

    @staticmethod
    def all_from_file(fname):
        valid_chars = {' ', '#', '.', '$', '*', '@', '+'}
        levels = []
        with open(fname, encoding = 'windows-1250') as f:
            level_lines = []
            for line in f:
                line = line.rstrip()
                if any(c not in valid_chars for c in line): line = ""
                if line: level_lines.append(line)
                elif level_lines:
                    levels.append(SokoLevel.from_lines(level_lines))
                    level_lines = []
            if level_lines: levels.append(SokoLevel.from_lines(level_lines))

        return levels

    def available_pos(self, pos):
        y,x = pos
        if not (0 <= y < self.height and 0 <= x < self.width): return False
        return not self.walls[pos]
