"""Models for the SEEKER app.

"""
from django.apps.config import AppConfig
from django.apps import apps
from django.db import models, transaction
from django.contrib.auth.models import User, Group
from django.db.models import Q
from django.db.models.functions import Lower
from django.db.models.query import QuerySet 
from django.utils.html import mark_safe
from django.utils import timezone
from django.forms.models import model_to_dict
import pytz
from django.urls import reverse
from datetime import datetime
import sys, os, io, re
import copy
import json
import time
import fnmatch
import csv
import math

from stalla.utils import *
from stalla.settings import APP_PREFIX, WRITABLE_DIR, TIME_ZONE

STANDARD_LENGTH=100
LONG_STRING=255
MAX_TEXT_LEN = 200
ABBR_LENGTH = 5
VISIT_MAX = 1400
VISIT_REDUCE = 1000

VIEW_STATUS = "view.status"
STATUS_TYPE = "seeker.stype"
AARD_TYPE = "seeker.aard"
MATTER_TYPE = "seeker.matter"

# ============ HELPER functions ================================

def get_crpp_date(dtThis, readable=False):
    """Convert datetime to string"""

    if readable:
        # Convert the computer-stored timezone...
        dtThis = dtThis.astimezone(pytz.timezone(TIME_ZONE))
        # Model: yyyy-MM-dd'T'HH:mm:ss
        sDate = dtThis.strftime("%d/%B/%Y (%H:%M)")
    else:
        # Model: yyyy-MM-dd'T'HH:mm:ss
        sDate = dtThis.strftime("%Y-%m-%dT%H:%M:%S")
    return sDate

def get_current_datetime():
    """Get the current time"""
    return timezone.now()

def get_now_time():
    """Get the current time"""
    return time.clock()

def build_choice_list(field, position=None, subcat=None, maybe_empty=False):
    """Create a list of choice-tuples"""

    choice_list = [];
    unique_list = [];   # Check for uniqueness

    try:
        # check if there are any options at all
        if FieldChoice.objects == None:
            # Take a default list
            choice_list = [('0','-'),('1','N/A')]
            unique_list = [('0','-'),('1','N/A')]
        else:
            if maybe_empty:
                choice_list = [('0','-')]
            for choice in FieldChoice.objects.filter(field__iexact=field):
                # Default
                sEngName = ""
                # Any special position??
                if position==None:
                    sEngName = choice.english_name
                elif position=='before':
                    # We only need to take into account anything before a ":" sign
                    sEngName = choice.english_name.split(':',1)[0]
                elif position=='after':
                    if subcat!=None:
                        arName = choice.english_name.partition(':')
                        if len(arName)>1 and arName[0]==subcat:
                            sEngName = arName[2]

                # Sanity check
                if sEngName != "" and not sEngName in unique_list:
                    # Add it to the REAL list
                    choice_list.append((str(choice.machine_value),sEngName));
                    # Add it to the list that checks for uniqueness
                    unique_list.append(sEngName)

            choice_list = sorted(choice_list,key=lambda x: x[1]);
    except:
        print("Unexpected error:", sys.exc_info()[0])
        choice_list = [('0','-'),('1','N/A')];

    # Signbank returns: [('0','-'),('1','N/A')] + choice_list
    # We do not use defaults
    return choice_list;

def build_abbr_list(field, position=None, subcat=None, maybe_empty=False, exclude=None):
    """Create a list of choice-tuples"""

    choice_list = [];
    unique_list = [];   # Check for uniqueness

    try:
        if exclude ==None:
            exclude = []
        # check if there are any options at all
        if FieldChoice.objects == None:
            # Take a default list
            choice_list = [('0','-'),('1','N/A')]
            unique_list = [('0','-'),('1','N/A')]
        else:
            if maybe_empty:
                choice_list = [('0','-')]
            for choice in FieldChoice.objects.filter(field__iexact=field):
                # Default
                sEngName = ""
                # Any special position??
                if position==None:
                    sEngName = choice.english_name
                elif position=='before':
                    # We only need to take into account anything before a ":" sign
                    sEngName = choice.english_name.split(':',1)[0]
                elif position=='after':
                    if subcat!=None:
                        arName = choice.english_name.partition(':')
                        if len(arName)>1 and arName[0]==subcat:
                            sEngName = arName[2]

                # Sanity check
                if sEngName != "" and not sEngName in unique_list and not (str(choice.abbr) in exclude):
                    # Add it to the REAL list
                    choice_list.append((str(choice.abbr),sEngName));
                    # Add it to the list that checks for uniqueness
                    unique_list.append(sEngName)

            choice_list = sorted(choice_list,key=lambda x: x[1]);
    except:
        print("Unexpected error:", sys.exc_info()[0])
        choice_list = [('0','-'),('1','N/A')];

    # Signbank returns: [('0','-'),('1','N/A')] + choice_list
    # We do not use defaults
    return choice_list;

def choice_english(field, num):
    """Get the english name of the field with the indicated machine_number"""

    try:
        result_list = FieldChoice.objects.filter(field__iexact=field).filter(machine_value=num)
        if (result_list == None):
            return "(No results for "+field+" with number="+num
        return result_list[0].english_name
    except:
        return "(empty)"

def choice_value(field, term):
    """Get the numerical value of the field with the indicated English name"""

    try:
        result_list = FieldChoice.objects.filter(field__iexact=field).filter(english_name__iexact=term)
        if result_list == None or result_list.count() == 0:
            # Try looking at abbreviation
            result_list = FieldChoice.objects.filter(field__iexact=field).filter(abbr__iexact=term)
        if result_list == None:
            return -1
        else:
            return result_list[0].machine_value
    except:
        return -1

def choice_abbreviation(field, num):
    """Get the abbreviation of the field with the indicated machine_number"""

    try:
        result_list = FieldChoice.objects.filter(field__iexact=field).filter(machine_value=num)
        if (result_list == None):
            return "{}_{}".format(field, num)
        return result_list[0].abbr
    except:
        return "-"

def get_help(field):
    """Create the 'help_text' for this element"""

    # find the correct instance in the database
    help_text = ""
    try:
        entry_list = HelpChoice.objects.filter(field__iexact=field)
        entry = entry_list[0]
        # Note: only take the first actual instance!!
        help_text = entry.get_text()
    except:
        help_text = "Sorry, no help available for " + field

    return help_text

def get_helptext(name):
    sBack = ""
    if name != "":
        sBack = HelpChoice.get_help_markdown(name)
    return sBack



# ================ STANDARD models ===============================
class FieldChoice(models.Model):

    field = models.CharField(max_length=50)
    english_name = models.CharField(max_length=100)
    dutch_name = models.CharField(max_length=100)
    abbr = models.CharField(max_length=20, default='-')
    machine_value = models.IntegerField(help_text="The actual numeric value stored in the database. Created automatically.")

    def __str__(self):
        return "{}: {}, {} ({})".format(
            self.field, self.english_name, self.dutch_name, str(self.machine_value))

    class Meta:
        ordering = ['field','machine_value']
        

class HelpChoice(models.Model):
    """Define the URL to link to for the help-text"""
    
    # [1] The 'path' to and including the actual field
    field = models.CharField(max_length=200)        
    # [1] Whether this field is searchable or not
    searchable = models.BooleanField(default=False) 
    # [1] Name between the <a></a> tags
    display_name = models.CharField(max_length=50)  
    # [0-1] The actual help url (if any)
    help_url = models.URLField("Link to more help", blank=True, null=True, default='')         
    # [0-1] One-line contextual help
    help_html = models.TextField("One-line help", blank=True, null=True)

    def __str__(self):
        return "[{}]: {}".format(
            self.field, self.display_name)

    def get_text(self):
        help_text = ''
        # is anything available??
        if self.help_url != None and self.help_url != '':
            if self.help_url[:4] == 'http':
                help_text = "See: <a href='{}'>{}</a>".format(
                    self.help_url, self.display_name)
            else:
                help_text = "{} ({})".format(
                    self.display_name, self.help_url)
        elif self.help_html != None and self.help_html != "":
            help_text = self.help_html
        return help_text

    def get_help_markdown(sField):
        """Get help based on the field name """

        oErr = ErrHandle()
        sBack = ""
        try:
            obj = HelpChoice.objects.filter(field__iexact=sField).first()
            if obj != None:
                sBack = obj.get_text()
                # Convert markdown to html
                sBack = markdown(sBack)
        except:
            msg = oErr.get_error_message()
            oErr.DoError("get_help")
        return sBack

# =================== HELPER models ===================================
class Status(models.Model):
    """Intermediate loading of sync information and status of processing it"""

    # [1] Status of the process
    status = models.CharField("Status of synchronization", max_length=50)
    # [1] Counts (as stringified JSON object)
    count = models.TextField("Count details", default="{}")
    # [0-1] Synchronisation type
    type = models.CharField("Type", max_length=255, default="")
    # [0-1] User
    user = models.CharField("User", max_length=255, default="")
    # [0-1] Error message (if any)
    msg = models.TextField("Error message", blank=True, null=True)

    def __str__(self):
        # Refresh the DB connection
        self.refresh_from_db()
        # Only now provide the status
        return self.status

    def set(self, sStatus, oCount = None, msg = None):
        self.status = sStatus
        if oCount != None:
            self.count = json.dumps(oCount)
        if msg != None:
            self.msg = msg
        self.save()


class Action(models.Model):
    """Track actions made by users"""

    # [1] The user
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_actions")
    # [1] The item (e.g: Manuscript, SermonDescr, SermonGold = M/S/SG/SSG)
    itemtype = models.CharField("Item type", max_length=MAX_TEXT_LEN)
    # [1] The ID value of the item (M/S/SG/SSG)
    itemid = models.IntegerField("Item id", default=0)
    # [0-1] possibly FK link to M/S/SG/SSG
    linktype = models.CharField("Link type", max_length=MAX_TEXT_LEN, null=True, blank=True)
    # [0-1] The ID value of the FK to M/S/SG/SSG
    linkid = models.IntegerField("Link id", null=True, blank=True)
    # [1] The kind of action performed (e.g: create, edit, delete)
    actiontype = models.CharField("Action type", max_length=MAX_TEXT_LEN)
    # [0-1] Room for possible action-specific details
    details = models.TextField("Detail", blank=True, null=True)
    # [1] Date and time of this action
    when = models.DateTimeField(default=get_current_datetime)

    def __str__(self):
        action = "{}|{}".format(self.user.username, self.when)
        return action

    def add(user, itemtype, itemid, actiontype, details=None):
        """Add an action"""

        # Check if we are getting a string user name or not
        if isinstance(user, str):
            # Get the user object
            oUser = User.objects.filter(username=user).first()
        else:
            oUser = user
        # If there are details, make sure they are stringified
        if details != None and not isinstance(details, str):
            details = json.dumps(details)
        # Create the correct action
        action = Action(user=oUser, itemtype=itemtype, itemid=itemid, actiontype=actiontype)
        if details != None: action.details = details
        action.save()
        return action

    def get_object(self):
        """Get an object representation of this particular Action item"""

        actiontype = self.actiontype
        model = ""
        oDetails = None
        changes = {}
        if actiontype == "save" or actiontype == "add" or actiontype == "new":
            oDetails = json.loads(self.details)
            actiontype = oDetails.get('savetype', '')
            changes = oDetails.get('changes', {})
            model = oDetails.get('model', None)

        when = self.when.strftime("%d/%B/%Y %H:%M:%S")
        oBack = dict(
            actiontype = actiontype,
            itemtype = self.itemtype,
            itemid = self.itemid,
            model = model,
            username = self.user.username,
            when = when,
            changes = changes
            )
        return oBack

    def get_history(itemtype, itemid):
        """Get a list of <Action> items"""

        lHistory = []
        # Get the history for this object
        qs = Action.objects.filter(itemtype=itemtype, itemid=itemid).order_by('-when')
        for item in qs:
            bAdd = True
            oChanges = item.get_object()
            if oChanges['actiontype'] == "change":
                if 'changes' not in oChanges or len(oChanges['changes']) == 0: 
                    bAdd = False
            if bAdd: lHistory.append(item.get_object())
        return lHistory


class Information(models.Model):
    """Specific information that needs to be kept in the database"""

    # [1] The key under which this piece of information resides
    name = models.CharField("Key name", max_length=255)
    # [0-1] The value for this piece of information
    kvalue = models.TextField("Key value", default = "", null=True, blank=True)

    class Meta:
        verbose_name_plural = "Information Items"

    def __str__(self):
        return self.name

    def get_kvalue(name):
        info = Information.objects.filter(name=name).first()
        if info == None:
            return ''
        else:
            return info.kvalue

    def set_kvalue(name, value):
        info = Information.objects.filter(name=name).first()
        if info == None:
            info = Information(name=name)
            info.save()
        info.kvalue = value
        info.save()
        return True

    def save(self, force_insert = False, force_update = False, using = None, update_fields = None):
        return super(Information, self).save(force_insert, force_update, using, update_fields)


class Visit(models.Model):
    """One visit to part of the application"""

    # [1] Every visit is made by a user
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_visits")
    # [1] Every visit is done at a certain moment
    when = models.DateTimeField(default=get_current_datetime)
    # [1] Every visit is to a 'named' point
    name = models.CharField("Name", max_length=STANDARD_LENGTH)
    # [1] Every visit needs to have a URL
    path = models.URLField("URL")

    def __str__(self):
        msg = "{} ({})".format(self.name, self.path)
        return msg

    def add(username, name, path, is_menu = False, **kwargs):
        """Add a visit from user [username]"""

        oErr = ErrHandle()
        try:
            # Sanity check
            if username == "": return True
            # Get the user
            user = User.objects.filter(username=username).first()
            # Adapt the path if there are kwargs
            # Add an item
            obj = Visit(user=user, name=name, path=path)
            obj.save()

            ## Get to the stack of this user
            #profile = Profile.objects.filter(user=user).first()
            #if profile == None:
            #    # There is no profile yet, so make it
            #    profile = Profile(user=user)
            #    profile.save()

            ## Process this visit in the profile
            #profile.add_visit(name, path, is_menu, **kwargs)

            # Possibly throw away an overflow of visit logs?
            user_visit_count = Visit.objects.filter(user=user).count()
            if user_visit_count > VISIT_MAX:
                # Check how many to remove
                removing = user_visit_count - VISIT_REDUCE
                # Find the ID of the first one to remove
                id_list = Visit.objects.filter(user=user).order_by('id').values('id')
                below_id = id_list[removing]['id']
                # Remove them
                Visit.objects.filter(user=user, id__lte=below_id).delete()
            # Return success
            result = True
        except:
            msg = oErr.get_error_message()
            oErr.DoError("visit/add")
            result = False
        # Return the result
        return result


class Stype(models.Model):
    """Status of M/S/SG/SSG"""

    # [1] THe abbreviation code of the status
    abbr = models.CharField("Status abbreviation", max_length=50)
    # [1] The English name
    nameeng = models.CharField("Name (ENglish)", max_length=50)
    # [1] The Dutch name
    namenld = models.CharField("Name (Dutch)", max_length=50)

    def __str__(self):
        return self.abbr


class NewsItem(models.Model):
    """A news-item that can be displayed for a limited time"""

    # [1] title of this news-item
    title = models.CharField("Title",  max_length=MAX_TEXT_LEN)
    # [1] the date when this item was created
    created = models.DateTimeField(default=get_current_datetime)
    saved = models.DateTimeField(null=True, blank=True)
    # [0-1] optional time after which this should not be shown anymore
    until = models.DateTimeField("Remove at", null=True, blank=True)
    # [1] the message that needs to be shown (in html)
    msg = models.TextField("Message")
    # [1] the status of this message (can e.g. be 'archived')
    status = models.CharField("Status", choices=build_abbr_list(VIEW_STATUS), 
                              max_length=5, help_text=get_help(VIEW_STATUS))

    def __str__(self):
        # A news item is the tile and the created
        sDate = get_crpp_date(self.created)
        sItem = "{}-{}".format(self.title, sDate)
        return sItem

    def save(self, force_insert = False, force_update = False, using = None, update_fields = None):
      # Adapt the save date
      self.saved = get_current_datetime()
      response = super(NewsItem, self).save(force_insert, force_update, using, update_fields)
      return response

    def check_until():
        """Check all news items for the until date and emend status where needed"""

        # Get current time
        now = timezone.now()
        for obj in NewsItem.objects.all():
            if obj.until and obj.until < now:
                # This should be set invalid
                obj.status = "ext"
                obj.save()
        # Return valid
        return True


# ==================== Stalla/Seeker models =============================


class IconClass(models.Model):
    """Iconclass"""

    # [1] Notatie
    notatie = models.CharField("Iconclass notatie",  max_length=MAX_TEXT_LEN)

    def __str__(self):
        return self.notatie


class Soort(models.Model):
    """Kind of woodcraft object"""

    # [1] Naam
    naam = models.CharField("Name (nl)",  max_length=MAX_TEXT_LEN)
    # [1] Naam
    eng = models.CharField("Name (en)",  max_length=MAX_TEXT_LEN)

    def __str__(self):
        return self.naam


class Tag(models.Model):
    """Each object can be described by zero or more tags"""

    # [1] Name
    name = models.CharField("Name",  max_length=MAX_TEXT_LEN)

    def __str__(self):
        return self.name


class Location(models.Model):
    """Location where a choir bank has been found"""

    # [1] Name of this location
    name = models.CharField("Location", max_length=MAX_TEXT_LEN)
    # [0-1] Country
    land = models.CharField("Country", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [0-1] City
    plaats = models.CharField("City", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [1] Location
    x_coordinaat = models.CharField("X coordinate", max_length=MAX_TEXT_LEN)
    # [1] Location
    y_coordinaat = models.CharField("Y coordinate", max_length=MAX_TEXT_LEN)

    def __str__(self):
        return self.name


class Kunstenaar(models.Model):
    """The artist involved"""

    # [1] Name of the artist
    name = models.CharField("Name",  max_length=MAX_TEXT_LEN)
    # [0-1] Date of birth
    geboortedatum = models.CharField("Date of birth", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [0-1] Date of death
    sterfdatum = models.CharField("Date of death", max_length=MAX_TEXT_LEN, blank=True, null=True)

    def __str__(self):
        return self.name


class Photographer(models.Model):
    """A photographer"""

    # [1] Name of the photographer
    name = models.CharField("Name",  max_length=MAX_TEXT_LEN)

    def __str__(self):
        return self.name


class Literatuur(models.Model):
    """A bibliographic piece"""

    # [0-1] Literature code
    literatuurcode = models.CharField("Literature code", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [0-1] Author
    auteursvermelding = models.CharField("Author", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [0-1] Title
    title = models.CharField("Title", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [0-1] Publication location
    plaatsvanuitgave = models.CharField("City", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [0-1] Year of publication
    jaar = models.CharField("Year", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [0-1] Journal
    tijdschrift = models.CharField("Journal", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [0-1] Year number
    jaarnummer = models.CharField("Year number", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [0-1] Page
    pagina = models.CharField("Page", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [0-1] Remark
    opmerking = models.CharField("Remark", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [0-1] Forced
    geforceerd = models.CharField("Forced", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [0-1] URL
    url = models.CharField("URL", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [0-1] Location where a copy of this publication is kept
    plaats = models.CharField("Location", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [1] Entered
    ingevoerd = models.BooleanField("Entered", default=False)
    # [1] Entered
    gecontroleerd = models.BooleanField("Checked", default=False)

    def __str__(self):
        return self.literatuurcode


class Werkstuk(models.Model):
    """An [object], i.e. some woodcraft created on a choir bank"""

    # [1] Inventory number
    inventarisnummer = models.CharField("Inventory number",  max_length=MAX_TEXT_LEN)
    # [1] Every codicological unit has a status - this is *NOT* related to model 'Status'
    aard = models.CharField("Area", choices=build_abbr_list(AARD_TYPE), max_length=5, default="uncl")
    # [0-1] Descriptions in Dutch
    beschrijving_nl = models.TextField("Description (nl)", blank=True, null=True)
    # [0-1] Descriptions in English
    beschrijving_en = models.TextField("Description (en)", blank=True, null=True)
    # [1] Nietopnet
    nietopnet = models.BooleanField("Nietopnet", default=False)
    # [0-1] Starting date
    begindatum = models.CharField("Start date", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [0-1] End date
    einddatum = models.CharField("End date", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [0-1] Measures
    afmetingen = models.CharField("Measures", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [1] Material
    materiaal = models.CharField("Materiaal", choices=build_abbr_list(MATTER_TYPE), max_length=5, default="eik")
    # [0-1] Condition
    toestand = models.CharField("Condition", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [0-1] Picture: start date
    begindatering_foto = models.CharField("Start date picture", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [0-1] Picture: End date
    einddatering_foto = models.CharField("End date picture", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [0-1] Measures
    afmetingen_foto = models.CharField("Measures picture", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [0-1] Lit paralel
    lit_paralel = models.TextField("Lit paralel", blank=True, null=True)
    # [0-1] Location of the choir bank
    plaats_koorbank = models.CharField("Choir bank location", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [0-1] Bearer
    drager = models.CharField("Bearer", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [0-1] Filepath
    filepath = models.CharField("File path", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [0-1] Jpg
    jpg = models.CharField("Jpg", max_length=MAX_TEXT_LEN, blank=True, null=True)

    # =============== Nummer codering =================================================
    # [0-1] End date 1
    nummer1 = models.CharField("Number 1", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [0-1] Vis bijschrift 1
    vis_bijschrift1 = models.CharField("Vis bijschrift 1", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [0-1] End date 2
    nummer2 = models.CharField("Number 2", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [0-1] Vis bijschrift 2
    vis_bijschrift2 = models.CharField("Vis bijschrift 2", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [0-1] End date 3
    nummer3 = models.CharField("Number 3", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [0-1] Vis bijschrift 3
    vis_bijschrift3 = models.CharField("Vis bijschrift 3", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [0-1] End date 4
    nummer4 = models.CharField("Number 4", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [0-1] Vis bijschrift 4
    vis_bijschrift4 = models.CharField("Vis bijschrift 4", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [0-1] End date 5
    nummer5 = models.CharField("Number 5", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [0-1] Vis bijschrift 5
    vis_bijschrift5 = models.CharField("Vis bijschrift 5", max_length=MAX_TEXT_LEN, blank=True, null=True)

    # [0-1] Dub number 1
    dubnummer1 = models.CharField("Dub number 1", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [0-1] Dubble picture text 1
    dubble_afb_tekst1 = models.CharField("Dubble picture text 1", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [0-1] Dub number 2
    dubnummer2 = models.CharField("Dub number 2", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [0-1] Dubble picture text 2
    dubble_afb_tekst2 = models.CharField("Dubble picture text 2", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [0-1] Dub number 3
    dubnummer3 = models.CharField("Dub number 3", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [0-1] Dubble picture text 3
    dubble_afb_tekst3 = models.CharField("Dubble picture text 3", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [0-1] Dub number 4
    dubnummer4 = models.CharField("Dub number 4", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [0-1] Dubble picture text 4
    dubble_afb_tekst4 = models.CharField("Dubble picture text 4", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [0-1] Dub number 5
    dubnummer5 = models.CharField("Dub number 5", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [0-1] Dubble picture text 5
    dubble_afb_tekst5 = models.CharField("Dubble picture text 5", max_length=MAX_TEXT_LEN, blank=True, null=True)

    # =============== Remarks on several things ========================================
    # [1] Remark on the date - Dutch
    opmerking_datering_nl = models.CharField("Date remark (nl)", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [1] Remark on the date - English
    opmerking_datering_en = models.CharField("Date remark (en)", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [1] Remark on the location
    opmerking_herkomstplaats = models.TextField("Remark on origin", blank=True, null=True)
    # [1] Remark on the location
    opmerking_toestand = models.TextField("Remark on condition", blank=True, null=True)
    # [1] Remark on the material
    opmerking_materiaal = models.TextField("Remark on material", blank=True, null=True)
    # [1] Remark on the picture
    opmerking_foto = models.TextField("Remark on picture", blank=True, null=True)
    # [1] Remark on the 'paralel'
    opmerking_paralel = models.TextField("Remark on paralel", blank=True, null=True)
    # [1] Remark on the date of the picture
    opmerking_datering_afb = models.TextField("Remark on picture date", blank=True, null=True)

    # ============== Foreign keys ======================================================
    # [1] Kind of object
    soort = models.ForeignKey(Soort, on_delete=models.CASCADE, related_name="soortwerkstukken")
    # [1] Location
    locatie = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="locatiewerkstukken")
    # [1] Photographer
    fotograaf = models.ForeignKey(Photographer, on_delete=models.CASCADE, related_name="fotograafwerkstukken")

    # ============== MANYTOMANY connections ============================================
    # [m] Many-to-many: tags per werkstuk
    tags = models.ManyToManyField(Tag, through="WerkstukTag", related_name="tags_werkstuk")
    # [m] Many-to-many: iconclasses per werkstuk
    iconclasses = models.ManyToManyField(IconClass, through="Iconclassnotatie", related_name="iconclasses_werkstuk")
    # [m] Many-to-many: artists per werkstuk
    kunstenaren = models.ManyToManyField(Kunstenaar, through="Kunstenaarnotatie", related_name="kunstenaren_werkstuk")
    # [m] Many-to-many: literature per werkstuk
    literaturen = models.ManyToManyField(Literatuur, through="Literatuurverwijzing", related_name="literaturen_werkstuk")

    def __str__(self):
        return self.inventarisnummer
            

class WerkstukTag(models.Model):
    """Link between werkstuk and tag"""

    # [1] THe link to the werkstuk
    werkstuk = models.ForeignKey(Werkstuk, on_delete=models.CASCADE, related_name="werkstuk_tag")
    # [1] THe link to the tag
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name="werkstuk_tag")
    # [1] And a date: the date of saving this relation
    created = models.DateTimeField(default=get_current_datetime)


class Iconclassnotatie(models.Model):
    """Link between iconclass and werkstuk"""

    # [1] THe link to the werkstuk
    werkstuk = models.ForeignKey(Werkstuk, on_delete=models.CASCADE, related_name="werkstuk_iconclass")
    # [1] THe link to the iconclass
    iconclass = models.ForeignKey(IconClass, on_delete=models.CASCADE, related_name="werkstuk_iconclass")
    # [0-1] Remark on this link
    opmerking = models.CharField("Remark", max_length=MAX_TEXT_LEN, blank=True, null=True)


class Kunstenaarnotatie(models.Model):
    """Link between werkstuk and tag"""

    # [1] THe link to the werkstuk
    werkstuk = models.ForeignKey(Werkstuk, on_delete=models.CASCADE, related_name="werkstuk_kunstenaar")
    # [1] THe link to the artist
    kunstenaar = models.ForeignKey(Kunstenaar, on_delete=models.CASCADE, related_name="werkstuk_kunstenaar")
    # [1] And a date: the date of saving this relation
    created = models.DateTimeField(default=get_current_datetime)


class Literatuurverwijzing(models.Model):
    """Link between literatuur and werkstuk"""

    # [1] THe link to the werkstuk
    werkstuk = models.ForeignKey(Werkstuk, on_delete=models.CASCADE, related_name="werkstuk_literatuur")
    # [1] THe link to the literature
    literatuur = models.ForeignKey(Literatuur, on_delete=models.CASCADE, related_name="werkstuk_literatuur")
    # [0-1] Page reference
    paginaerwijzing = models.CharField("Page reference", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [1] Whether an item of this literature is in possession or not
    exemplaar = models.BooleanField(default=False) 
    # [0-1] ROom for a remark
    opmerking = models.TextField("Opmerking", blank=True, null=True)




