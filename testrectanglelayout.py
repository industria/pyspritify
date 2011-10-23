import unittest

import sys

from rectanglelayout import Node
from rectanglelayout import Layout
from rectanglelayout import RectangleLayoutError

class TestLayout(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass


    def test_layout_raises_out_of_space(self):
        root = Node(0, 0, 10, 10)
        layout = Layout(root)
        self.assertRaises(RectangleLayoutError, layout.insert, 12, 12, "fail")



    def test_layout_locked_width(self):
        root = Node(0, 0, 12, sys.maxint)

        layout = Layout(root)

        layout.insert(12, 2, 1)
        layout.insert(10, 4, 2)
        layout.insert(10, 2, 3)
        layout.insert(8, 4, 4)
        layout.insert(8, 4, 5)
        layout.insert(6, 2, 6)
        layout.insert(6, 4, 7)
        layout.insert(4, 2, 8)
        layout.insert(4, 2, 9)
        layout.insert(2, 2, 10)
        layout.insert(2, 2, 11)
        layout.insert(2, 2, 12)
        layout.insert(2, 2, 13)
        layout.insert(2, 2, 14)
        
        layout.prune()


if __name__ == '__main__':
    unittest.main()
