import imghdr
from optparse import OptionParser
from optparse import OptionGroup
import os
import os.path
import re
import string
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
        self.cssfilename = None
        self.cssClassname = None
        self.cssimagepath = None
        self.spriteFilename = None
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
        parser.add_option("-f", "--stop", action="store_true", default=False, dest="stop", help="Stop if PIL fails to open an image file, normal operation is simply skipping files that can't be opened.")
        # Group for CSS options
        cssGroup = OptionGroup(parser, "CSS options")
        cssGroup.add_option("-c", "--css", dest="css", default="sprite.css", help="Name of the CSS file. (Default: sprite.css)")
        cssGroup.add_option("-n", "--classname", dest="classname", default=".sprite", help="Name of the CSS class defining the background url. (Default: .sprite)")
        cssGroup.add_option("-p", "--cssimagepath", dest="cssimagepath", default="", help="Path to prefix the sprite name with in the background-image url. Should be used if the sprite and CSS files are not written to the same directory.")
        parser.add_option_group(cssGroup)
        # Group for sprite options
        spriteGroup = OptionGroup(parser, "Sprite options")
        spriteGroup.add_option("-s", "--sprite", dest="sprite", default="sprite.png", help="Name of the sprite file. (Default: sprite.png)")
        parser.add_option_group(spriteGroup)
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
        self.cssfilename = os.path.abspath(os.path.expanduser(options.css))
        self.cssClassname = options.classname
        self.cssimagepath = options.cssimagepath
        self.spriteFilename = os.path.abspath(os.path.expanduser(options.sprite))
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
        self.filename = filename

    def __str__(self):
        """
        String representation of a SprintImage.
        """
        return "%s width=%s height=%s" % (self.filename, self.width, self.height)


class Spritify(object):
    """
    Spritify a directory of images based on a SpritifyConfiguration.
    """
    def __init__(self, configuration):
        """
        Create a Spritify object with using a SpritifyConfiguration.
        """
        self.__conf = configuration
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
                if self.__conf.stop:
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
        width = 0
        height = 0
        for image in images:
            width = max(width, image.width)
            height = max(height, image.height)
        if(width < height):
            width = sys.maxint
        else:
            height = sys.maxint
        return (width, height)


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


    def _layoutSprintImages(self, images):
        """
        Layout the sprite images in a container that is only bound be height or width
        depending on which is largest the other dimension will de unlimited in size
        and the final height and width of the sprite will be determined when the layout
        is complete. 

        images: List of SpriteImage objects to layout
        """
        (width, height) = self._virtualSpriteSize(images)
        print "Virtual sprite size %s x %s" % (width, height)
        layout = Layout(width, height)
        sorted_images = self._sortSpriteImages(images, width, height)
        for image in sorted_images:
            layout.insert(image.width, image.height, image)
        layout.prune()
        return layout
        (actual_width, actial_height) = layout.bounding()


    def _drawLayout(self, layout):
        """
        Draw an image from the layout.
        """
        (image_width, image_height) = layout.bounding()
        print "Draw image: ", image_width, image_height
        sprint = Image.new("RGBA", (image_width, image_height))
        
        for node in layout.nodes():
            sprint.paste(node.item._image, (node.x, node.y))
            print node
        sprint.save(self.__conf.spriteFilename, "PNG")


    def _spriteClassFromNode(self, node):
        """
        Get a sprite class name from a node.
        """
        filename = node.item.filename
        basename = os.path.basename(filename)
        match = re.search("""^[^\.]+""", basename)
        if(match is None):
            return "somedafault"
        else:
            return match.group(0)


    def _writeCSS(self, layout):
        """
        Write the CSS for the layout.
        """
        css = open(self.__conf.cssfilename, "w")
        # Register the image as background:url
        url = self.__conf.cssimagepath + os.path.basename(self.__conf.spriteFilename)
        css.write(str.format("{0} {{background-image: url(\"{1}\");}}\n",  self.__conf.cssClassname, url))
        # Register the images as classes by there filenames
        for node in layout.nodes():
            name = self._spriteClassFromNode(node)
            css.write(str.format(".{0} {{", name))
            css.write(str.format("width: {0}px; height: {1}px; ", node.width, node.height))
            css.write(str.format("background-position: {0}px {1}px;", 0 - node.x, 0 - node.y))
            css.write("}\n");
        css.close()

    def generate(self):
        """
        Generate the sprite and CSS file
        """
        print "Traverse directory %s for images" % ( self.__conf.directory)
        print "Verbose output:", self.__conf.verbose

        sprite_images = self._buildImageList(self.__conf.imagefiles)
        layout = self._layoutSprintImages(sprite_images)        
        self._drawLayout(layout)
        self._writeCSS(layout)


if __name__ == '__main__':
    conf = SpritifyConfiguration()
    sprite = Spritify(conf)
    sprite.generate()

