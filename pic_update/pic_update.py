import sys, traceback
import os
from pathlib import Path
import zipfile
import tarfile
import shutil


class ErrHandle:
    """Error handling"""

    # ======================= CLASS INITIALIZER ========================================
    def __init__(self):
        # Initialize a local error stack
        self.loc_errStack = []

    # ----------------------------------------------------------------------------------
    # Name :    Status
    # Goal :    Just give a status message
    # History:
    # 6/apr/2016    ERK Created
    # ----------------------------------------------------------------------------------
    def Status(self, msg):
        # Just print the message
        print(msg, file=sys.stderr)

    # ----------------------------------------------------------------------------------
    # Name :    DoError
    # Goal :    Process an error
    # History:
    # 6/apr/2016    ERK Created
    # ----------------------------------------------------------------------------------
    def DoError(self, msg, bExit = False):
        # Append the error message to the stack we have
        self.loc_errStack.append(msg)
        # get the message
        sErr = self.get_error_message()
        # Print the error message for the user
        print("Error: {}\nSystem:{}".format(msg, sErr), file=sys.stderr)
        # Is this a fatal error that requires exiting?
        if (bExit):
            sys.exit(2)
        # Otherwise: return the string that has been made
        return "<br>".join(self.loc_errStack)

    def get_error_message(self):
        arInfo = sys.exc_info()
        if len(arInfo) == 3:
            sMsg = str(arInfo[1])
            if arInfo[2] != None:
                sMsg += " at line " + str(arInfo[2].tb_lineno)
            return sMsg
        else:
            return ""

    def get_error_stack(self):
        return " ".join(self.loc_errStack)

def move_dir_to_targz(subdir, imgdir):
    print("Doing tar.gz of images in: {}".format(imgdir))
    targetfile = "./{}/stalla_img_{}.tar.gz".format(subdir, imgdir)
    # Walk all files in this subdirectory
    reading_dir = os.path.join(subdir, imgdir)
    with tarfile.open(targetfile, "w:gz") as tar:
        for fn in os.listdir(reading_dir):
            p = os.path.join(reading_dir, fn)
            arcname = os.path.join(imgdir, fn)
            tar.add(p, arcname=arcname)
    # Remove the directory
    print("Removing directory: {}".format(reading_dir))
    shutil.rmtree(reading_dir)

def unzip_archive(archive):
    """Unzip [archive] to a directory structure based on it"""

    # Keep track of directories
    directories = []

    # Figure out what the subdir is
    subdir = archive.filename[0:len(archive.filename)-4]

    for file in archive.namelist():
        # Check if this is a JPG
        if ".jpg" in file.lower():
            # Get the name of the file after /
            arName = file.split("/")
            filename = arName[-1].lower()
            # Get the first two characters of the name of the file
            dir_name = filename[0:2]
            # Directory check
            if not dir_name in directories:
                directories.append(dir_name)
                print("Doing directory {}".format(dir_name))

            # Extract to this directory
            targetdir = Path("./{}/{}".format(subdir, dir_name))
            # Check if this directory exists
            if not targetdir.exists():
                targetdir.mkdir()

            targetfile = "./{}/{}/{}".format(subdir, dir_name, filename)
            targetpath = Path(targetfile)
            if not targetpath.exists():
                # Read the data
                data = archive.read(file)
                targetpath.write_bytes(data)

    # Close the archive
    archive.close()
    # Return the directories and the subdir
    return subdir, directories

errHandle = ErrHandle()


# ----------------------------------------------------------------------------------
# Name :    main
# Goal :    Main body of the function
# History:
# 31/jan/2022    ERK Created
# ----------------------------------------------------------------------------------
def main(prgName, argv) :
    flInput = ''        # input file name, e.g: 'lowresscans_2022jan31.zip'
    flOutput = ""       # Output directory
    language = "en"     # Default language

    try:
        sSyntax = prgName + ' -i <input zip file>'
        # get all the arguments
        try:
            # Get arguments and options
            opts, args = getopt.getopt(argv, "hi:", ["-input="])
        except getopt.GetoptError:
            print(sSyntax)
            sys.exit(2)
        # Walk all the arguments
        for opt, arg in opts:
            if opt in ("-h", "--help"):
                print(sSyntax)
                sys.exit(0)
            elif opt in ("-i", "--inputfile"):
                flInput = arg

        # Check if all arguments are there
        if (flInput == ''):
            errHandle.DoError(sSyntax, True)

        # Main code
        archive = zipfile.ZipFile(flInput)
        errHandle.Status("Treating archive: {}".format(flInput))

        subdir, directories = unzip_archive(archive)

        errHandle.Status("Moving image directories to TAR.gz...")
        for imgdir in directories:
            move_dir_to_targz(subdir, imgdir)


        errHandle.Status("Ready")
    except:
        # act
        errHandle.DoError("main")
        return False



# ----------------------------------------------------------------------------------
# Goal :  If user calls this as main, then follow up on it
# ----------------------------------------------------------------------------------
if __name__ == "__main__":
  # Call the main function with two arguments: program name + remainder
  main(sys.argv[0], sys.argv[1:])


