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
        self.writeHtmlOverview = None
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
        description = """Create a sprint and a corresponding CSS file from images in the directory argument. If the directory isn't supplied the current directory will be used."""
        parser = OptionParser(usage = usage, version=version, description=description)
        parser.add_option("-v", "--verbose", action="store_true", default=False, dest="verbose", help="Verbose output during sprite and CSS generation.")
        parser.add_option("-f", "--stop", action="store_true", default=False, dest="stop", help="Stop if PIL fails to open an image file, normal operation is simply skipping files that can't be opened.")
        parser.add_option("-o", "--nooverview", action="store_false", default=True, dest="overview", help="HTML overview file will be created if this option is set. The file is named overview.html and written in current directory.")
        # Group for CSS options
        cssGroup = OptionGroup(parser, "CSS options")
        cssGroup.add_option("-c", "--css", dest="css", default="sprite.css", help="Name of the CSS file. (Default: sprite.css)")
        cssGroup.add_option("-n", "--classname", dest="classname", default="sprite", help="Name of the CSS class defining the background url. Don't prefix the classname with a period that is done by the CSS writer. (Default: sprite)")
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
        self.writeHtmlOverview = options.overview
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
            parser.error(str.format("{0} is not a directory", arg_dir))
        self.directory = arg_dir
        # Check for image files in the directory and fail with parse error if no
        # image files where found in the directory tree.
        self.imagefiles = self._imagefiles(arg_dir)
        if(0 == len(self.imagefiles)):
            parser.error(str.format("No image files found in {0}", self.directory))


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
        Initialize a SpriteImage with a PIL image and
        the full path filename of the PIL image.
        """
        self.image = image
        (self.width, self.height) = self.image.size
        self.filename = filename

    def __str__(self):
        """
        String representation of a SprintImage.
        """
        return str.format("{0} width={1} height={2}", self.filename, self.width, self.height)


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
                    print str.format("Error: PIL failed to open [{0}], with {1}", f, ioe)
                    sys.exit(1);
                else:
                    print str.format("Skipping file [{0}], PIL error: {1}", f, ioe)
        return sprite_images


    def _virtualSpriteSize(self, images):
        """
        Find the virtual sprite size, which is a sprite where either 
        width or height is open-ended (sys.maxint) depending on
        which dimension has the largest size among the images.
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
        """
        (width, height) = self._virtualSpriteSize(images)
        print str.format("Virtual sprite size {0} x {1}", width, height)
        layout = Layout(width, height)
        sorted_images = self._sortSpriteImages(images, width, height)
        for image in sorted_images:
            layout.insert(image.width, image.height, image)
        layout.prune()
        return layout

    def _drawLayout(self, layout):
        """
        Draw an image, the sprite, from a layout.
        """
        (image_width, image_height) = layout.bounding()
        print "Draw image: ", image_width, image_height
        sprite = Image.new("RGBA", (image_width, image_height))
        for node in layout.nodes():
            sprite.paste(node.item.image, (node.x, node.y))
            print node
        sprite.save(self.__conf.spriteFilename, "PNG")


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
        Write CSS for the layout returning a list of classes in the file.
        """
        css = open(self.__conf.cssfilename, "w")
        # Register the image as background:url
        url = self.__conf.cssimagepath + os.path.basename(self.__conf.spriteFilename)
        css.write(str.format(".{0} {{background-image: url(\"{1}\");}}\n",  self.__conf.cssClassname, url))
        # Register the images as classes by there filenames
        cssClasses = []
        for node in layout.nodes():
            name = self._spriteClassFromNode(node)
            cssClasses.append(name)
            css.write(str.format(".{0} {{", name))
            css.write(str.format("width: {0}px; height: {1}px; ", node.width, node.height))
            css.write(str.format("background-position: {0}px {1}px;", 0 - node.x, 0 - node.y))
            css.write("}\n");
        css.close()
        return cssClasses

    def _writeHtml(self, cssClasses):
        """
        Write an overview HTML document referencing all classes added
        to the CSS file written.
        """
        html = open("overview.html", "w")
        html.write("<!DOCTYPE html><html><head><meta charset=\"utf-8\">")
        html.write(str.format("<link rel=\"stylesheet\" type=\"text/css\" href=\"{0}\" />", self.__conf.cssfilename))
        html.write("</head><body>")
        for cssClass in cssClasses:
            html.write(str.format("<div>{0} {1}</div>\n", self.__conf.cssClassname, cssClass))
            html.write(str.format("<div class=\"{0} {1}\"></div>\n", self.__conf.cssClassname, cssClass))
            html.write("<hr>\n")
        html.write("""</body></html>""")
        html.close()


    def generate(self):
        """
        Generate the sprite and CSS file
        """
        print str.format("Traverse directory {0} for images", self.__conf.directory)
        print "Verbose output:", self.__conf.verbose

        sprite_images = self._buildImageList(self.__conf.imagefiles)
        layout = self._layoutSprintImages(sprite_images)        
        self._drawLayout(layout)
        cssClasses = self._writeCSS(layout)
        print "Classes in the CSS", cssClasses
        if self.__conf.writeHtmlOverview:
            self._writeHtml(cssClasses)

if __name__ == '__main__':
    conf = SpritifyConfiguration()
    sprite = Spritify(conf)
    sprite.generate()

