__author__ = 'Quentin Roy'
from block import Block


class Run:
    def __init__(self, dom, xp):
        self._dom = dom
        self._xp = xp
        self._id = self._dom.attrib["id"]
        self._blocks = []

        # create the blocks
        for block_dom in self._dom.iter():
            if block_dom.tag in ("block", "practice"):
                block = Block(block_dom, self, len(self._blocks))
                self._blocks.append(block)

    @property
    def id(self):
        return self._id

    @property
    def xp(self):
        return self._xp

    def block(self, block_num):
        return self._blocks[block_num]

    def iter_blocks(self):
        return (block for block in self._blocks)

    def __len__(self):
        return len(self._blocks)

    def completed(self):
        for block in self.iter_blocks():
            if not block.completed():
                return False
        return True

    def started(self):
        for block in self.iter_blocks():
            if block.started():
                return True
        return False