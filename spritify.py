import imghdr
from optparse import OptionParser
import os
import os.path
import sys
from PIL import Image

from rectanglelayout import Layout
from rectanglelayout import RectangleLayoutError


class SpritifyConfiguration(object):
    """
    Create a configuration for running the spritification from the command line arguments supplied.
    """
    def __init__(self):
        """
        Create a SprifityConfiguration object by parsing command line arguments.
        """
        self.directory = None
        self.verbose = None
        self.stop = None
        self.imagefiles = None
        parser = self._setupOptionParser()
        self._parseArguments(parser)
        parser.destroy()
        pass

    def _setupOptionParser(self):
        """
        Setup the OptionParser for the command line parsing.
        """
        usage = """usage: %prog [options] directory"""
        version = """%prog 0.1"""
        description = """Create a sprint and a corresponding CSS file from images in the directory argument. 
                         If the directory isn't supplied the current directory will be used."""
        parser = OptionParser(usage = usage, version=version, description=description)
        parser.add_option("-v", "--verbose", action="store_true", default=False, dest="verbose", help="Verbose output during sprite and CSS generation.")
        parser.add_option("-s", "--stop", action="store_true", default=False, dest="stop", help="Stop if PIL fails to open an image file, normal operation is simply skipping files that can't be opened.")

        #    op.add_option("-c", "--file", dest="file", help="Configuration file with appid, appkey and host")
        #    op.add_option("-i", "--appid", dest="appid", help="Override application id in configuration file")
        #    op.add_option("-k", "--appkey", dest="appkey", help="Override application key in configuration file")
        #    op.add_option("-d", "--host", dest="host", help="Override userservice host in configuration file")
        #    op.add_option("-p", "--prop", action="store_true", default=False, dest="prop", help="Get user properties for username")
        #    op.add_option("-b", "--branding", dest="branding", help="Branding to use when activating reset.")
        #    op.add_option("-u", "--user", dest="user", help="Python dict representation of a user (parsed using eval()).")
        #    op.add_option("", "--delete", action="store_true", default=False, dest="delete", help="Delete the user. NOTE: this doesn't ask twice.")
        return parser

    def _parseArguments(self, parser):
        """
        Parse the command line arguments with the OptionParser supplied in the parser argument
        and supply the validation of the positional argument directory and other
        options that needs further validation before the configuration is finalized.
        """
        (options, arguments) = parser.parse_args()
        self.verbose = options.verbose
        self.stop = options.stop
        # Directory will be current working directory unless a positional argument is
        # supplied on the command line. If the argument isn't a directory it's considered
        # a parse error.
        if(0 == len(arguments)):
            arg_dir = os.getcwd()
        else:
            arg_dir = os.path.abspath(arguments[0])
        if not os.path.isdir(arg_dir):
            parser.error("%s is not a directory" % (arg_dir))
        self.directory = arg_dir
        # Check for image files in the directory and fail with parse error if no
        # image files where found in the directory tree.
        self.imagefiles = self._imagefiles(arg_dir)
        if(0 == len(self.imagefiles)):
            parser.error("Directory %s doesn't contain any image files" % (self.directory))
        pass


    def _imagefiles(self, directory):
        """
        Traverse the directory and get a list of all images in the directory tree.
        Image files are detected using imghdr module and all file returning 
        something other that None will be included in the image file list.
        """
        imagefiles = []
        for root, dirs, files in os.walk(directory):
            for filename in files:
                absfilename = os.path.join(root, filename);
                imagetype = imghdr.what(absfilename)
                if not None is imagetype:
                    imagefiles.append(absfilename)
        return imagefiles


class SpriteImage(object):
    """
    Represents an image to include in the sprite.
    Its basically a container holding a PIL Image of the actual image
    and metadata about the image to facilitate placing the image in
    the final sprite.
    """
    def __init__(self, image, filename):
        """
        Initialize a SpriteImage object.

        image : PIL image.
        filename : Full path filename to the image.
        """
        self._image = image
        (self.width, self.height) = self._image.size
        self.area = self.width * self.height
        self.filename = filename
        self.x = 0
        self.y = 0

    def __str__(self):
        """
        String representation of a SprintImage.
        """
        return "%s (%s, %s) width=%s height=%s" % (self.filename, self.x, self.y, self.width, self.height)


    def setPosition(self, x, y):
        """
        Set the image sprite position.
        """
        self.x = x
        self.y = y


class SpriteLayoutNode(object):
    """
    Node in the sprite layout tree.
    """
    def __init__(self, x, y, width, height):
        """
        Initialize a SpriteLayoutNode.
        """
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.image = None
        self.left = None
        self.right = None

    def __str__(self):
        """
        String representation of a SpriteLayoutNode.
        """
        return "(%s, %s) w=%s h=%s" % (self.x, self.y, self.width, self.height)


    def canContainImage(self, image):
        """
        Check if image image can fit inside the node.
        It fits if not image is assigned to the node  and the dimensions
        of the image fits inside the node.
        """
        if(not self.image is None):
            return False;
        return ((image.width <= self.width) and (image.height <= self.height))


class SpriteLayout(object):
    """
    Implement the sprite layout algorithm.
    """
    def __init__(self, width, height):
        """
        Initialize the sprite layout by supplying the width and height
        of the virtual sprite.
        """
        self.tree = SpriteLayoutNode(0, 0, width, height)
        self._bbox_width = 0
        self._bbox_height = 0

    def _findLayoutNode(self, node, image):
        """
        Find a SpriteLayoutNode that can fit the image.
        """
        if(node is None):
            return None

        if (node.canContainImage(image)):
            return node
        else:
            leftnode = self._findLayoutNode(node.left, image)
            if(not leftnode is None):
                return leftnode
            else:
                return self._findLayoutNode(node.right, image)


    def _areaBelowImage(self, node, image):
        """
        Calcualte the area left below the image when the image size
        has been allocated from the node.

        node  : SpriteLayoutNode the image is allocated from.
        image : The image to allocate from the node.

        return : SpriteLayoutNode representing the free space below
                 the allocated image. None if no space is left.
        """
        free_area = None
        x = node.x
        y = node.y + image.height + 1
        width = node.width
        height = node.height - image.height
        if(0 < height):
            free_area = SpriteLayoutNode(x, y, width, height)
        return free_area

    def _areaRightOfImage(self, node, image):
        """
        Calculate the area left to the right of the image when the
        image size has been allocated from the node.

        node  : SpriteLayoutNode the image is allocated from.
        image : The image to allocate from the node.
        
        return : SpriteLayoutNode representing the free space to the
                 right of the allocated image. None if no space is left.
        """
        free_area = None
        x = node.x + image.width + 1
        y = node.y
        width = node.width - image.width
        height = image.height
        if(0 < width):
            free_area = SpriteLayoutNode(x, y, width, height)
        return free_area

    def insert(self, image):
        """
        Insert an image into the SpriteLayout.
        
        image : SpriteImage to add to the layout.
        """
        freenode = self._findLayoutNode(self.tree, image)
        if(freenode is None):
            # No free node was found meaning the image will not
            # fit into the sprite. This should never happen when
            # using the open-ended virtual sprite.
            print "No more space in sprite"
            sys.exit(1)
        # Place the image into the free node by assigning the
        # image reference to the node and setting the free node
        # upper left corner to the position of the image in the sprite.
        freenode.image = image
        image.setPosition(freenode.x, freenode.y)
        # There will be an area of free space below and to the right
        # of the image placed in the node.
        free_area_below = self._areaBelowImage(freenode, image)
        free_area_right = self._areaRightOfImage(freenode, image)
        # Place the smalleste area as the left child in the tree.
        # This is because the traversal always picks the left child 
        # node first when looking for a free node and allocation should
        # happen from finit size node before using the open-ended node.
        if((free_area_below is None) or (free_area_right is None)):
            # Left or right position doesn't really matter.
            freenode.left = free_area_below
            freenode.right = free_area_right
        else:
            # Left should be the node with the lowest area
            area_below = free_area_below.width * free_area_below.height
            area_right = free_area_right.width * free_area_right.height
            if(area_below < area_right):
                freenode.left = free_area_below
                freenode.right = free_area_right
            else:
                freenode.left = free_area_right
                freenode.right = free_area_below


    def _bbox(self, node, width, height):
        """
        Bounding box by traversing the layout.
        width and height are updated during traversal.
        """
        if(node is None):
            return (width, height)

        if(node.image is None):
            return (width, height)

        width = max(node.x + node.image.width, width)
        height = max(node.y + node.image.height, height)

        if(not node.left is None):
            (width, height) = self._bbox(node.left, width, height)

        if(not node.right is None):
            (width, height) = self._bbox(node.right, width, height)
        
        return (width, height)    


    def boundingBox(self):
        """
        Get the bounding box of the layout.
        Return a 4-tuple (x, y, width, height)
        """
        (width, height) = self._bbox(self.tree, 0, 0)
        return (0, 0, width, height)
        

class Spritify(object):
    """
    Spritify a directory of images based on a SpritifyConfiguration.
    """
    def __init__(self, configuration):
        """
        Create a Spritify object with using a SpritifyConfiguration.
        """
        self._configuration = configuration
        pass

    def _buildImageList(self, imagefilenames):
        """
        Build a list of SpriteImage objects from a list of image filenames.
        """
        sprite_images = []
        for f in imagefilenames:
            try:
                img = Image.open(f)
                sprite_image = SpriteImage(img, f)
                sprite_images.append(sprite_image)
            except IOError as ioe:
                if self._configuration.stop:
                    print "Error: PIL failed to open [%s], with %s" % (f, ioe)
                    sys.exit(1);
                else:
                    print "Skipping file [%s], PIL error: %s" % (f, ioe)
        return sprite_images


    def _virtualSpriteSize(self, images):
        """
        Find the virtual sprite size, which is a sprite where either 
        width or height is unlimited (that is sys.maxint) depending 
        on with dimension has the largest size among the images.

        images : List of SpriteImages to the virtual sprite size from.
        return: (width, height)
        """
        maximum_width = 0
        maximum_height = 0
        for image in images:
            maximum_width = max(maximum_width, image.width)
            maximum_height = max(maximum_height, image.height)
        if(maximum_width < maximum_height):
            maximum_width = sys.maxint
        else:
            maximum_height = sys.maxint
        return (maximum_width, maximum_height)


    def _sortSpriteImages(self, images, width, height):
        """
        Sort the sprite images according the the fixed dimension of the virtual
        sprite size, which is basically the smallest dimension. 

        images: List of SpriteImage objects to be sorted
        width: Virtual sprite width
        height: Virtual sprite height

        Return list of images sorted according to the dimensions of the virtual sprite size.
        """
        if (width < height):
            key_function =  lambda sprite_image: sprite_image.width
        else:
            key_function = lambda sprite_image: sprite_image.height
        return sorted(images, reverse = True, key = key_function);

    def _spriteSize(self, layout):
        """
        Calculate the actual sprite size needed for the layout.

        layout: SpriteLayout with all images assigned.

        Return size of the sprite as a 2-tuple (width, height)
        """
        (x, y, width, height) = layout.boundingBox()
        print "Box: ", x, y, width, height
        return (width, height)


    def _layoutSprintImages(self, images):
        """
        Layout the sprite images in a container that is only bound be height or width
        depending on which is largest the other dimension will de unlimited in size
        and the final height and width of the sprite will be determined when the layout
        is complete. 

        images: List of SpriteImage objects to layout
        """
        (vwidth, vheight) = self._virtualSpriteSize(images)
        print "Virtual sprite size %s x %s" % (vwidth, vheight)
        layout = Layout(vwidth, vheight)
        sorted_images = self._sortSpriteImages(images, vwidth, vheight)
        for image in sorted_images:
            layout.insert(image.width, image.height, image)
        layout.prune()
        print layout.bounding()


    def generate(self):
        print "Traverse directory %s for images" % ( self._configuration.directory)
        print "Verbose output:", self._configuration.verbose

        sprite_images = self._buildImageList(self._configuration.imagefiles)
        self._layoutSprintImages(sprite_images)        



if __name__ == '__main__':
    conf = SpritifyConfiguration()
    sprite = Spritify(conf)
    sprite.generate()

