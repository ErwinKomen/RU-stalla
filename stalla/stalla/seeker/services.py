"""
SEEKER app: different services
"""
import os
import subprocess


# From own code
from stalla.settings import MEDIA_DIR
from stalla.seeker.models import Information
from stalla.utils import ErrHandle

if os.path.exists("/mnt/d") or os.path.exists("D:/"):
    SHELL_CMD="wsl sh"
    BATCH_ROOT = "/home/erwin/do_mdbprocess.sh"
else:
    SHELL_CMD="sh"
    BATCH_ROOT = "/var/www/writable/media/stalla/do_mdbprocess.sh"


def process_mdbprocess(oStatus):
    """Process an uploaded MDB"""

    oBack = dict(result=False)

    batch_name = "/home/erwin/"
    oErr = ErrHandle()
    try:
        oStatus.set("preparing")

        # Get the file name and the user
        mdbuploaded = Information.get_kvalue("mdbuploaded")
        mdbuser = Information.get_kvalue("mdbuser")

        # get the full filename
        filepath = os.path.abspath(os.path.join(MEDIA_DIR, "stalla", mdbuploaded))
        # Check if it is there
        if os.path.exists(filepath):
            oStatus.set("Path exists")
            # Yes, we may continue
            # Define the batch file command
            sCmd = "{} {} {}".format(SHELL_CMD, BATCH_ROOT, mdbuploaded)
 
            oStatus.set("Waiting for shell")
            p = subprocess.run(sCmd, shell=True, check=True, capture_output=True, timeout=90, encoding="utf-8")
            oStatus.set("Shell finished")
            # Get the result
            print(f'Command {p.args} exited with {p.returncode} code, output: \n{p.stdout}')
           
            # Show all is well
            oBack['result'] = True
        else:
            # Set error message in back
            oBack['msg'] = "Uploaded MDB file not found: {}".format(filepath)
            oBack['result'] = False
    except:
        oStatus.set("error")
        oErr.DoError("process_mdbprocess", True)
    # Return the result
    return oBack

