import unittest

import sys

from rectanglelayout import Layout
from rectanglelayout import RectangleLayoutError

class TestLayout(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass


    def test_layout_raises_out_of_space(self):
        layout = Layout(10, 10)
        self.assertRaises(RectangleLayoutError, layout.insert, 12, 12, "fail")

    def test_layout_locked_width(self):
        layout = Layout(12, sys.maxint)
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
        (width, height) = layout.bounding()
        self.assertEqual(12, width)
        self.assertEqual(22, height)
        
        node_count = 0
        for node in layout.nodes():
            node_count = node_count + 1
        self.assertEqual(14, node_count)


if __name__ == '__main__':
    unittest.main()
