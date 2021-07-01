"""
Adaptations of the database that are called up from the (list)views in the SEEKER app.
"""

from django.db import transaction
import re

# ======= imports from my own application ======
from stalla.utils import ErrHandle
from stalla.seeker.models import Information, User, Group, NewsItem, Visit, Status, \
    Werkstuk, WerkstukTag, Location, City, Country


adaptation_list = {
    "werkstuk_list": ['materiaal', 'double_tags', 'locations'],
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

def adapt_double_tags():
    oErr = ErrHandle()
    bResult = True
    msg = ""
    
    try:
        # Walk all the werkstuk objects
        with transaction.atomic():
            for obj in Werkstuk.objects.all():
                delete_lst = []
                tag_lst = []
                # Get all the tags for this object
                for taglink in WerkstukTag.objects.filter(werkstuk_id=obj.id).values('id', 'werkstuk_id', 'tag_id'):
                    if taglink['tag_id'] not in tag_lst:
                        tag_lst.append(taglink['tag_id'])
                    else:
                        delete_lst.append(taglink['id'])
                # Remove the culprits
                WerkstukTag.objects.filter(id__in=delete_lst).delete()
    except:
        bResult = False
        msg = oErr.get_error_message()
    return bResult, msg


def adapt_locations():
    oErr = ErrHandle()
    bResult = True
    msg = ""
    
    try:
        # Walk all the werkstuk objects
        with transaction.atomic():
            for obj in Location.objects.all().order_by('country__name', 'city__name'):
                # Process the city/country 
                if obj.city == None:
                    # Process the country
                    land = obj.land
                    if land == "": land = "onbekend"
                    country = Country.objects.filter(name=land).first()
                    if country == None:
                        country = Country.objects.create(name=land)

                    # Process the city
                    plaats = obj.plaats
                    if plaats == "": plaats = "onbekend"
                    city = City.objects.filter(name=plaats, country=country).first()
                    if city == None:
                        city = City.objects.create(name=plaats, country=country)
                    # Seet the correct country and city in the Location
                    obj.city = city
                    obj.country = country
                    obj.save()
                elif obj.country == None:
                    # Get the city
                    city = obj.city
                    # Get the country of that city
                    country = city.country
                    # Set my country
                    obj.country = country
                    obj.save()

 
    except:
        bResult = False
        msg = oErr.get_error_message()
        oErr.DoError("adapt_locations")
    return bResult, msg

