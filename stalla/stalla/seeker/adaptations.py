"""
Adaptations of the database that are called up from the (list)views in the SEEKER app.
"""

from django.db import transaction
import re

# ======= imports from my own application ======
from stalla.utils import ErrHandle
from stalla.seeker.models import Information, User, Group, NewsItem, Visit, Status, \
    Werkstuk


adaptation_list = {
    "werkstuk_list": ['materiaal'],
    'sermon_list': ['nicknames', 'biblerefs'],
    'sermongold_list': ['sermon_gsig'],
    'equalgold_list': ['author_anonymus', 'latin_names', 'ssg_bidirectional', 's_to_ssg_link', 
                       'hccount', 'scount', 'ssgcount', 'ssgselflink', 'add_manu', 'passim_code'],
    'provenance_list': ['manuprov_m2m']
    }

def listview_adaptations(lv):
    """Perform adaptations specific for this listview"""

    oErr = ErrHandle()
    try:
        if lv in adaptation_list:
            for adapt in adaptation_list.get(lv):
                sh_done  = Information.get_kvalue(adapt)
                if sh_done == None or sh_done != "done":
                    # Do the adaptation, depending on what it is
                    method_to_call = "adapt_{}".format(adapt)
                    bResult, msg = globals()[method_to_call]()
                    if bResult:
                        # Success
                        Information.set_kvalue(adapt, "done")
    except:
        msg = oErr.get_error_message()
        oErr.DoError("listview_adaptations")

def adapt_materiaal():
    oErr = ErrHandle()
    bResult = True
    msg = ""
    
    try:
        # Walk all the werkstuk objects
        with transaction.atomic():
            for obj in Werkstuk.objects.all():
                materiaal = obj.materiaal
                if materiaal == "Onbekend":
                    materiaal = "unkn"
                elif materiaal == "Notenhout":
                    materiaal = "noot"
                elif materiaal == "Eikenhout":
                    materiaal = "eik"
                obj.materiaal = materiaal
                obj.save()
    except:
        bResult = False
        msg = oErr.get_error_message()
    return bResult, msg



