__copyright__ = """
Copyright 2011 James Lindstorff

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

class RectangleLayoutError(Exception):
    """
    Error raised when the rectangle layout fails.
    """
    def __init__(self, value):
        """
        Initialize the error with a value.
        """
        self.value = value

    def __str__(self):
        """
        String representation of the layout error.
        """
        return repr(self.value)

class PartitioningDirection(object):
    """
    Represents partitioning directions.
    """
    X, Y = range(2)


class Node(object):
    """
    Represents a node in the layout tree.
    The node has information about placement, x and y, 
    extent, width and height, and whether the node
    is allocated, plus an item property which can be used
    to associate application specific references to the node.
    The Node also has a left and a right property which is
    references to the Node childs in the layout tree.
    """
    def __init__(self, x, y, width, height, allocated = False, item = None):
        """
        Initialize a Node with a placement and an extent. 
        Optionally the allocated marker and the item can be set.
        """
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.allocated = allocated
        self.item = item
        self.left = None
        self.right = None

    def __str__(self):
        return "[%s] - (%s, %s) w=%s h=%s" % (self.item, self.x, self.y, self.width, self.height)

    area = property(lambda self : self.width * self.height, None, None, None)


class Layout(object):
    """
    Represents and builds the rectangle layout.
    The rectangles are represented as Node objects and
    the layout is a binary tree structure build by 
    subsequent insertions of Node objects into the 
    layout. The layout supports openended directions
    by placing the smallest node from a split to the
    left in the layout tree and finally by supplying
    support methods to calculate the actual area used
    by the rectangles (nodes) placed in the layout.
    """
    def __init__(self, width, height):
        """
        Initialize the layout with a width and height representing
        the initial free space the following rectangles should
        fit within. If one of the directions should be open-ended
        set the size of the dimension to sys.maxint or a similar
        large value that will not be exhausted. Take care not setting
        both directions to open-ended because the rectangles added will
        end up in a single row or column so one direction should be locked.
        """
        self._root = Node(0, 0, width, height)
        self._partitioning = self.__selectPartitioning(width, height)
        self._free_node = None
        self._allocated = []

    def __selectPartitioning(self, width, height):
        """
        Select the partitioning direction to used based on
        the width and height the layout was initialized with.
        Directions the larger direction will determine the
        partitioning used and if equal the Y direction is used.
        """
        if(width > height):
            return PartitioningDirection.X
        else:
            return PartitioningDirection.Y

    def __traverse(self, node, width, height):
        """
        Traverse the tree for first usable node
        that is not allocated and will fit the
        recgtangle, width and height.
        """
        if((not node is None) and (self._free_node is None)):
            self.__traverse(node.left, width, height)
            if((not node.allocated) and (width <= node.width and height <= node.height)):
                self._free_node = node
            self.__traverse(node.right, width, height)


    def __findFreeSpace(self, width, height):
        """
        Traverse the layout tree for a free space node
        where the rectangle defined by the width and height
        will fit. If a free space node could not be found
        it means the initial rectangle space has been
        exhausted and None will be returned.
        """
        self._free_node = None
        self.__traverse(self._root, width, height)
        return self._free_node

    def __freeSpaceBelowAllocation(self, node, width, height):
        """
        Calculate the free space area left below the rectangle defined
        by the width and the height when it's allocated from
        the node. The free space is returned as a node.
        """
        x_below = node.x
        y_below = node.y + height
        height_below = node.height - height
        # The width is calculated differently depending on
        # direction of the open-endedness
        if(PartitioningDirection.Y == self._partitioning):
            width_below = node.width
        elif(PartitioningDirection.X == self._partitioning):
            width_below = width
        else:
            raise RectangleLayoutError("Unknown partitioning direction")
        return Node(x_below, y_below, width_below, height_below)


    def __freeSpaceBesideAllocation(self, node, width, height):
        """
        Calculate the free space area left beside the rectangle defined
        by the width and the height when it's allocated from
        the node. The free space is returned as a node.
        """
        x_beside = node.x + width
        y_beside = node.y
        width_beside = node.width - width
        # The height is calculated differently depending on
        # direction of the open-endedness
        if(PartitioningDirection.Y == self._partitioning):
            height_beside = height
        elif(PartitioningDirection.X == self._partitioning):
            height_beside = node.height
        else:
            raise RectangleLayoutError("Unknown partitioning direction")
        return Node(x_beside, y_beside, width_beside, height_beside)

        
    def insert(self, width, height, item):
        """
        Insert a rectangle into the layout by supplying 
        width, height and an item reference.
        This will find the first available node in the layout
        tree where the rectangle will fit. A new node will be
        inserted into the free node found by splitting it into
        an area below and an area to the right of the inserted
        node. The free space node with the smallest area will
        be inserted on the left child while the one with the
        largest area will be inserted on the right child.
        """
        node = self.__findFreeSpace(width, height)
        if(node is None):
            raise RectangleLayoutError("No free space left in the layout")
        print "Allocate from", node
        # Place the rectangle into the layout starting by calculating
        # the free space areas that will be left when the rectangle
        # has been allocated from the node.
        node_below = self.__freeSpaceBelowAllocation(node, width, height)
        node_beside = self.__freeSpaceBesideAllocation(node, width, height)
        # Allocate the rectangle in the node
        node.allocated = True
        node.item = item
        node.width = width
        node.height = height
        # Add the allocated node to the allocated list
        self._allocated.append(node)
        print "After allocation", node
        # Place the smallest free space area to the left in the tree
        if(node_below.area < node_beside.area):
            node.left = node_below
            node.right = node_beside
        else:
            node.left = node_beside
            node.right = node_below
        # Check if the left and right nodes are usabled taking
        # area of the in to account and set unusable nodes to None.
        if(0 >= node.left.area):
            node.left = None
        if(0 >= node.right.area):
            node.right = None
        print "Left:", node.left
        print "Right:", node.right
        print "-----------------------------------------------"


    def __prune_traverse(self, node):
        """
        Traverse the layout tree removing unallocated nodes.
        """
        if(not node is None):
            self.__prune_traverse(node.left)
            if((not node.left is None) and (not node.left.allocated)):
                node.left = None
            if((not node.right is None) and (not node.right.allocated)):
                node.right = None
            self.__prune_traverse(node.right)

    def prune(self):
        """
        Prune the layout tree by removing all unallocated nodes.
        """
        self.__prune_traverse(self._root)


    def __bounding_traverse(self, node, width, height):
        """
        Traverse the layout tree calculating the bounding box.
        """
        max_width = width
        max_height = height
        if(not node is None):
            (max_width_left, max_height_left) = self.__bounding_traverse(node.left, max_width, max_height)
            (max_width_right, max_height_right) = self.__bounding_traverse(node.right, max_width, max_height)
            max_width = max(max_width, max_width_left, max_width_right, node.x + node.width)
            max_height = max(max_height, max_height_left, max_height_right, node.y + node.height)
        return (max_width, max_height)

    def bounding(self):
        """
        Return the width and height of the layouts bounding rectangle.
        Its returned as a 2-tuple (width, height).
        """
        (width, height) = self.__bounding_traverse(self._root, 0, 0)
        return (width, height)


    def nodes(self):
        """
        Generator function for nodes in the layout.
        """
        for node in self._allocated:
            yield node

            
