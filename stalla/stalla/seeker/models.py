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
from multiprocessing import Process
from multiprocessing import Pipe
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
from stalla.seeker.excel import excel_to_list, excel_generator
from stalla.settings import APP_PREFIX, WRITABLE_DIR, TIME_ZONE, MEDIA_DIR

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

def custom_add(oWerkstuk, cls, idfield, addonly=False, **kwargs):
    """Add or change a werkstuk according to the specifications provided"""

    oErr = ErrHandle()
    manu = None
    lst_msg = []
    lstQ = {}
    app_name = "seeker"
    bNeedsSaving = False
    accessid = "undefined"
    field = "undefined"
    value = "undefined"

    try:
        profile = kwargs.get("profile")
        username = kwargs.get("username")
        team_group = kwargs.get("team_group")

        # Obligatory: accessid
        accessid = oWerkstuk.get(idfield.lower())

        # Retrieve or create a new werkstuk with default values
        if addonly:
            obj = None
        else:
            obj = cls.objects.filter(accessid=accessid).first()
        if obj == None:
            # Doesn't exist: create it
            # obj = cls.objects.create(accessid=accessid)
            lstQ['accessid'] = accessid
                        
        # Process all fields in the Specification
        for oField in cls.specification:
            # Make sure to take the lower-case variant of the name
            field = oField.get("name").lower()
            value = oWerkstuk.get(field)
            readonly = oField.get('readonly', False)
            optional = (oField.get('optional') == True)
            if value != None and value != "" and not readonly:
                path = oField.get("path")
                if path == None: path = field
                type = oField.get("type")
                if type == None: type = "field"
                if type == "field":
                    if isinstance(value, str):
                        value = value.strip()
                    # Possibly correct for field type
                    if value in ['True', 'False']:
                        value = True if value == "True" else False

                    # Set the correct field's value
                    if obj == None:
                        lstQ[path] = value
                    elif getattr(obj,path) != value:
                        if path == "lit_paralel":
                            iStop = 1
                        # Log change
                        oErr.Status("custom_add change {} from {} into {}".format(path,getattr(obj,path), value ))
                        # Perform the change
                        setattr(obj, path, value)
                        bNeedsSaving = True
                elif type == "intfield":
                    # Convert to integer if needed
                    if isinstance(value, str):
                        try:
                            value = int(value)
                        except:
                            # Shwo what has gone wrong
                            msg = "ERROR: at accessid={} cannot convert field [{}], value [{}] into integer. Using [0]".format(accessid, field, value)
                            oErr.Status(msg)
                            # Use the default value '0', which may be completely wrong
                            value = 0

                    # Set the correct field's value
                    if obj == None:
                        lstQ[path] = value
                    elif getattr(obj,path) != value:
                        # Log change
                        oErr.Status("custom_add change {} from {} into {}".format(path,getattr(obj,path), value ))
                        # Perform the change
                        setattr(obj, path, value)
                        bNeedsSaving = True
                elif type == "fk":
                    fkfield = oField.get("fkfield")
                    model = oField.get("model")
                    if fkfield != None and model != None:
                        # Find an item with the name for the particular model
                        cls = apps.app_configs[app_name].get_model(model)
                        instance = cls.objects.filter(**{"{}".format(fkfield): value}).first()
                        if instance != None:
                            if obj == None:
                                lstQ[path]  = instance
                            elif getattr(obj,path) != instance:
                                # Log change
                                org = getattr(obj,path)
                                original = "None" if org is None else org.id
                                target = "None" if instance is None else instance.id
                                oErr.Status("custom_add change {} from {} into {}".format(path, original, target ))
                                # Perform the change
                                setattr(obj, path, instance)
                                bNeedsSaving = True
                elif type == "func":
                    # Set the KV in a special way
                    if obj == None:
                        # Creating a new one: response will be dictionary
                        oResponse = cls.custom_set(None, path, value, oWerkstuk, **kwargs)
                        if oResponse != None:
                            for k,v in oResponse.items():
                                lstQ[k] = v
                    else:
                        # Existing one: response will be boolean
                        if obj.custom_set(path, value, oWerkstuk, **kwargs):
                            bNeedsSaving = True

        # Make sure the update the object
        if obj == None:
            # Create one
            obj = cls.objects.create(**lstQ)
        elif bNeedsSaving:
            # Save the changes
            obj.save()
    except:
        html = []
        html.apend(oErr.get_error_message())
        if not accessid is None:
            html.append("accessid={}".format(accessid))
        if not field is None:
            html.append("field={}".format(field))
        if not value is None:
            html.append("value={}".format(value))
        msg = "custom_add. {}".format("; ".join(html))
        oErr.DoError(msg)
    return obj

def custom_getkv(obj, item, **kwargs):
    """Get key and value from the manuitem entry"""

    oErr = ErrHandle()
    key = ""
    value = ""
    try:
        key = item['name']
        if self != None:
            if item['type'] == 'field':
                value = getattr(obj, item['path'])
            elif item['type'] == "fk":
                fk_obj = getattr(obj, item['path'])
                if fk_obj != None:
                    value = getattr( fk_obj, item['fkfield'])
            elif item['type'] == 'func':
                value = obj.custom_get(item['path'], kwargs=kwargs)
                # Adaptation for empty lists
                if value == "[]": value = ""
    except:
        msg = oErr.get_error_message()
        oErr.DoError("custom_getkv")
    return key, value

# ================ Application specific ==========================
def process_userdata(oStatus):
    """Read userdata from an Excel file"""

    oBack = {}
    oErr = ErrHandle()

    try:
        oStatus.set("preparing")
        # Process changes in user-data as made available in Excel in the media directory
        filename = os.path.abspath(os.path.join(MEDIA_DIR, "stalla", "StallaTables.xlsx"))

        oResult = Werkstuk.read_excel(oStatus, filename)

        # We are done!
        oStatus.set("done", oBack)

        # return positively
        oBack['result'] = True
        return oBack
    except:
        oStatus.set("error")
        oErr.DoError("process_userdata", True)
        return oBack

def process_jsondata(oStatus):
    """Read userdata from JSON files"""

    oBack = {}
    oErr = ErrHandle()
    lst_table = ["object", "iconclass", "Kunstenaar", "literatuur",
                 "iconclassnotatie", "Kunstenaarnotatie", "literatuurverwijzing"]
    try:
        oStatus.set("preparing")

        # Get the filename of the combined JSON
        filename = os.path.abspath(os.path.join(MEDIA_DIR, "stalla", "StallaTables.json"))
        # Does it exist?
        if os.path.exists(filename):
            oStatus.set("re-using existing JSON")

            # Read the JSON data into an object
            with open(filename, "r", encoding="utf-8") as fp:
                oStallaData = json.load(fp)
        else:
            # Need to create it

            # Read and combine the JSON table files
            oStallaData = {}
            for tblName in lst_table:
                tbl_this = []

                # We are reading this file
                oBack['table'] = tblName
                oStatus.set("reading", oBack)

                # Get full path
                tblFile = os.path.abspath(os.path.join(MEDIA_DIR, "stalla", "{}.json".format(tblName)))
                # Read table
                with open(tblFile, "r", encoding="utf-8") as fp:
                    for line in fp:
                        oLine = json.loads(line)
                        # Change all keys to lower case
                        oNew = {k.lower(): v for k,v in oLine.items()}
                        tbl_this.append(oNew)
                # Add this table to the data
                oStallaData[tblName] = tbl_this

            # We are saving this file
            oBack['table'] = "Saving new JSON"
            oBack['file'] = filename
            oStatus.set("saving", oBack)

            with open(filename, "w", encoding="utf-8") as fp:
                json.dump(oStallaData, fp, indent=2)

        # We are saving this file
        oBack['table'] = "all done"
        oBack['file'] = "saved"
        oStatus.set("saving", oBack)

        oResult = Werkstuk.read_json(oStatus, data=oStallaData)

        # We are done!
        oStatus.set("done", oBack)

        # return positively
        oBack['result'] = True
        return oBack
    except:
        oStatus.set("error")
        oErr.DoError("process_userdata", True)
        return oBack



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

    # [1] Take over the access ID
    accessid = models.IntegerField("Access ID")
    # [1] Notatie
    notatie = models.CharField("Iconclass notatie",  max_length=MAX_TEXT_LEN)

    # Scheme for downloading and uploading
    specification = [
        # Note: name=Excel file, path=Db field name
        {'name': 'iconclassID',         'type': 'field',    'path': 'accessid'},
        {'name': 'iconclassnotatie',    'type': 'field',    'path': 'notatie'},
        ]

    def __str__(self):
        return self.notatie


class Soort(models.Model):
    """Kind of woodcraft object"""

    # [1] Naam
    naam = models.CharField("Name (nl)",  max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [1] Naam
    eng = models.CharField("Name (en)",  max_length=MAX_TEXT_LEN, blank=True, null=True)

    def __str__(self):
        return self.naam


class Tag(models.Model):
    """Each object can be described by zero or more tags"""

    # [1] Name
    abbr = models.CharField("Abbreviation",  max_length=MAX_TEXT_LEN, blank=True)
    # [1] Name
    name = models.CharField("Name (nld)",  max_length=MAX_TEXT_LEN)
    # [0-1] Name
    eng = models.CharField("Name (eng)",  max_length=MAX_TEXT_LEN, blank=True)
    # [0-1] Field
    field = models.CharField("Field in object",  max_length=MAX_TEXT_LEN, blank=True)

    def __str__(self):
        return self.name


class Country(models.Model):
    """Location where a choir bank has been found"""

    # [1] Name of this location
    name = models.CharField("Name", max_length=MAX_TEXT_LEN)

    def __str__(self):
        return self.name


class City(models.Model):
    """Location where a choir bank has been found"""

    # [1] Name of this location
    name = models.CharField("Name", max_length=MAX_TEXT_LEN)
    # [1] Every city belongs to a country
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="countrycities")

    def __str__(self):
        return self.name


class Location(models.Model):
    """Location where a choir bank has been found"""

    # [1] Name of this location
    name = models.CharField("Location", max_length=MAX_TEXT_LEN)
    # [0-1] City
    city = models.ForeignKey(City, blank=True, null=True, on_delete=models.CASCADE, related_name="citylocations")
    # [0-1] Country
    country = models.ForeignKey(Country, blank=True, null=True, on_delete=models.CASCADE, related_name="countrylocations")
    # [1] Location
    x_coordinaat = models.CharField("X coordinate", max_length=MAX_TEXT_LEN)
    # [1] Location
    y_coordinaat = models.CharField("Y coordinate", max_length=MAX_TEXT_LEN)

    def __str__(self):
        return self.name


class Kunstenaar(models.Model):
    """The artist involved"""

    # [1] Take over the access ID
    accessid = models.IntegerField("Access ID")
    # [1] Name of the artist
    name = models.CharField("Name",  max_length=MAX_TEXT_LEN)
    # [0-1] Date of birth
    geboortedatum = models.CharField("Date of birth", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [0-1] Date of death
    sterfdatum = models.CharField("Date of death", max_length=MAX_TEXT_LEN, blank=True, null=True)

    # Scheme for downloading and uploading
    specification = [
        # Note: name=Excel file, path=Db field name
        {'name': 'KunstenaarID',        'type': 'field',    'path': 'accessid'},
        {'name': 'Kunstenaarnotatie',   'type': 'field',    'path': 'name'},
        ]

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

    # [1] Take over the access ID
    accessid = models.IntegerField("Access ID")
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

    # Scheme for downloading and uploading
    specification = [
        # Note: name=Excel file, path=Db field name
        {'name': 'literatuurID',        'type': 'field',    'path': 'accessid'},
        {'name': 'literatuurcode'},
        {'name': 'auteursvermelding'},
        {'name': 'titel', 'path': 'title'},
        {'name': 'plaatsvanuitgave'},
        {'name': 'jaar'},
        {'name': 'tijdschrift'},
        {'name': 'jaarnummer'},
        {'name': 'pagina'},
        {'name': 'opmerking'},
        {'name': 'geforceerd'},
        {'name': 'plaats'},
        {'name': 'ingevoerd'},
        {'name': 'url'},
        {'name': 'gecontroleerd'},
        ]

    def __str__(self):
        return self.literatuurcode


class Werkstuk(models.Model):
    """An [object], i.e. some woodcraft created on a choir bank"""

    # [1] Take over the access ID
    accessid = models.IntegerField("Access ID")
    # [1] Inventory number
    inventarisnummer = models.CharField("Inventory number",  max_length=MAX_TEXT_LEN)
    # [1] Every werkstuk has a particular 'aard'
    aard = models.CharField("Area", choices=build_abbr_list(AARD_TYPE), max_length=5, default="uncl")
    # [0-1] Descriptions in Dutch
    beschrijving_nl = models.TextField("Description (nl)", blank=True, null=True)
    # [0-1] Descriptions in English
    beschrijving_en = models.TextField("Description (en)", blank=True, null=True)
    # [1] Nietopnet
    nietopnet = models.BooleanField("Nietopnet", default=False)
    # [0-1] Starting date
    begindatum = models.IntegerField("Start date", blank=True, null=True)   # max_length=MAX_TEXT_LEN, 
    # [0-1] End date
    einddatum = models.IntegerField("End date", blank=True, null=True)      # max_length=MAX_TEXT_LEN, 
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
    fotograaf = models.ForeignKey(Photographer, on_delete=models.CASCADE, related_name="fotograafwerkstukken", null=True)

    # ============== MANYTOMANY connections ============================================
    # [m] Many-to-many: tags per werkstuk
    tags = models.ManyToManyField(Tag, through="WerkstukTag", related_name="tags_werkstuk")
    # [m] Many-to-many: iconclasses per werkstuk
    iconclasses = models.ManyToManyField(IconClass, through="Iconclassnotatie", related_name="iconclasses_werkstuk")
    # [m] Many-to-many: artists per werkstuk
    kunstenaren = models.ManyToManyField(Kunstenaar, through="Kunstenaarnotatie", related_name="kunstenaren_werkstuk")
    # [m] Many-to-many: literature per werkstuk
    literaturen = models.ManyToManyField(Literatuur, through="Literatuurverwijzing", related_name="literaturen_werkstuk")

    # Scheme for downloading and uploading
    specification = [
        # Note: name=Excel file, path=Db field name
        {'name': 'accessid',            'type': 'field',    'path': 'objectid'},
        {'name': 'inventarisnummer',    'type': 'field',    'path': 'inventarisnummer'},
        {'name': 'aard',                'type': 'func',     'path': 'aard'},
        {'name': 'beschrijving_ned',    'type': 'field',    'path': 'beschrijving_nl'},
        {'name': 'beschrijving_eng',    'type': 'field',    'path': 'beschrijving_en'},
        {'name': 'nietopnet',           'type': 'field',    'path': 'nietopnet'},
        {'name': 'begindatum',          'type': 'intfield', 'path': 'begindatum'},
        {'name': 'einddatum',           'type': 'intfield', 'path': 'einddatum'},
        {'name': 'afmetingen',          'type': 'field',    'path': 'afmetingen'},
        {'name': 'materiaal',           'type': 'func',     'path': 'materiaal'},
        {'name': 'toestand',            'type': 'field',    'path': 'toestand'},
        {'name': 'begindatering_foto',  'type': 'field',    'path': 'begindatering_foto'},
        {'name': 'einddatering_foto',   'type': 'field',    'path': 'einddatering_foto'},
        {'name': 'afmetingen_foto',     'type': 'field',    'path': 'afmetingen_foto'},
        {'name': 'lit_paralel',         'type': 'field',    'path': 'lit_paralel'},
        {'name': 'plaats_koorbank',     'type': 'field',    'path': 'plaats_koorbank'},
        {'name': 'drager',              'type': 'field',    'path': 'drager'},
        {'name': 'filepath',            'type': 'field',    'path': 'filepath'},
        {'name': 'jpg',                 'type': 'field',    'path': 'jpg'},

        {'name': 'fotograaf',           'type': 'func',     'path': 'fotograaf', 'optional': True},
        {'name': 'locatie',             'type': 'func',     'path': 'locatie'},
        {'name': 'soort',               'type': 'func',     'path': 'soort'},
        {'name': 'soort_engels',        'type': 'func',     'path': 'soort'},

        {'name': 'nummer1',             'type': 'field', 'path': 'nummer1'},
        {'name': 'vis_bijschrift1',     'type': 'field', 'path': 'vis_bijschrift1'},
        {'name': 'nummer2',             'type': 'field', 'path': 'nummer2'},
        {'name': 'vis_bijschrift2',     'type': 'field', 'path': 'vis_bijschrift2'},
        {'name': 'nummer3',             'type': 'field', 'path': 'nummer3'},
        {'name': 'vis_bijschrift3',     'type': 'field', 'path': 'vis_bijschrift3'},
        {'name': 'nummer4',             'type': 'field', 'path': 'nummer4'},
        {'name': 'vis_bijschrift4',     'type': 'field', 'path': 'vis_bijschrift4'},
        {'name': 'nummer5',             'type': 'field', 'path': 'nummer5'},
        {'name': 'vis_bijschrift5',     'type': 'field', 'path': 'vis_bijschrift5'},

        {'name': 'dubnummer1',          'type': 'field', 'path': 'dubnummer1'},
        {'name': 'dubble_afb_tekst1',   'type': 'field', 'path': 'dubble_afb_tekst1'},
        {'name': 'dubnummer2',          'type': 'field', 'path': 'dubnummer2'},
        {'name': 'dubble_afb_tekst2',   'type': 'field', 'path': 'dubble_afb_tekst2'},
        {'name': 'dubnummer3',          'type': 'field', 'path': 'dubnummer3'},
        {'name': 'dubble_afb_tekst3',   'type': 'field', 'path': 'dubble_afb_tekst3'},
        {'name': 'dubnummer4',          'type': 'field', 'path': 'dubnummer4'},
        {'name': 'dubble_afb_tekst4',   'type': 'field', 'path': 'dubble_afb_tekst4'},
        {'name': 'dubnummer5',          'type': 'field', 'path': 'dubnummer5'},
        {'name': 'dubble_afb_tekst5',   'type': 'field', 'path': 'dubble_afb_tekst5'},

        {'name': 'opmerking_datering',          'type': 'field', 'path': 'opmerking_datering_nl'},
        {'name': 'opmerking_datering_engels',   'type': 'field', 'path': 'opmerking_datering_en'},
        {'name': 'opmerking_herkomstplaats',    'type': 'field', 'path': 'opmerking_herkomstplaats'},
        {'name': 'opmerkingen',                 'type': 'field', 'path': 'opmerking_toestand'},
        {'name': 'opmerking_materiaal',         'type': 'field', 'path': 'opmerking_materiaal'},
        {'name': 'opmerking_foto',              'type': 'field', 'path': 'opmerkingen_foto'},
        {'name': 'opmerking_paralel',           'type': 'field', 'path': 'opmerkingen_paralel'},
        {'name': 'opmerking_datering_afb',      'type': 'field', 'path': 'opmerkingen_datering_afb'},
        ]
    afbeeldingen = {
        "nummer1": "vis_bijschrift1", "nummer2": "vis_bijschrift2", 
        "nummer3": "vis_bijschrift3", "nummer4": "vis_bijschrift4", "nummer5": "vis_bijschrift5",
        "dubnummer1": "dubble_afb_tekst1", "dubnummer2": "dubble_afb_tekst2", "dubnummer3": "dubble_afb_tekst3", 
        "dubnummer4": "dubble_afb_tekst4", "dubnummer5": "dubble_afb_tekst5"}


    class Meta:
        verbose_name = "object"
        verbose_name_plural = "objecten"

    def __str__(self):
        return self.inventarisnummer

    def custom_get(self, path, **kwargs):
        sBack = ""
        oErr = ErrHandle()
        try:
            profile = kwargs.get("profile")
            username = kwargs.get("username")
            team_group = kwargs.get("team_group")

            # Specific path handling
            if path == "aard":
                sBack = choice_value(AARD_TYPE, self.aard)

        except:
            msg = oErr.get_error_message()
            oErr.DoError("Werkstuk/custom_get")
        return sBack

    def custom_m2m(oWerkstuk, clsTarget, clsM2m, rel, fk, extra_fields = None):
        """"""

        oErr = ErrHandle()
        try:
            # Get the objectid (access id)
            werkstuk = Werkstuk.objects.filter(accessid=oWerkstuk['objectid']).first()
            if not werkstuk is None:
                # Get the current iconclass accessids for Iconclass
                target = [x['targetid'] for x in oWerkstuk['values']]
                # Get the current list of iconclass access id's
                current = getattr(werkstuk, rel).all() # werkstuk.werkstuk_iconclass.all()
                oCurrent = { getattr(x, fk).accessid : getattr(x, fk).id for x in current}
                # Add relations that are not in there
                for oItem in oWerkstuk['values']:
                    targetid = oItem['targetid']
                    if not targetid in oCurrent:
                        # Add this relation
                        obj = clsTarget.objects.filter(accessid=targetid).first()
                        accessid = oItem['accessid']
                        args = dict(werkstuk=werkstuk, accessid=accessid)
                        args[fk] = obj

                        # Possibly add extra fields
                        if not extra_fields is None:
                            for extra in extra_fields:
                                value = oItem.get(extra)
                                if not value is None:
                                    args[extra] = value

                        clsM2m.objects.create(**args)
                # Remove relations that should be deleted
                delete_id = []
                for obj in current:
                    # Check if this accessid should actually occur in the target
                    targetid = getattr(obj, fk).accessid # obj.iconclass.accessid
                    if not targetid in target:
                        # No, it may not occur: add the correct information in [delete_id]
                        delete_id.append(obj.id)
                if len(delete_id) > 0:
                    clsM2m.objects.filter(id__in=delete_id).delete()
        except:
            msg = oErr.get_error_message()
            oErr.DoError("Werkstuk/custom_set")
            lstQ = {} if self is None else False

    def custom_set(self, path, value, oWerkstuk, **kwargs):
        """Set related items"""

        oErr = ErrHandle()
        aard_abbr = {"4": "prof", "5": "reli", "6": "uncl"}
        materiaal_abbr = dict(eikenhout= "eik", 
                              notenhout="noot", 
                              grenenhout="gre",
                              kalksteen="kal",
                              onbekend="unkn")
        lstQ = {}
        try:
            # The nature of [lstQ] depends on whether we are creating something new or not
            if not self is None:
                lstQ = False

            # Make sure we have the right information
            profile = kwargs.get("profile")
            username = kwargs.get("username")
            team_group = kwargs.get("team_group")

            value_lst = []
            if isinstance(value, str) and value[0] != '[':
                value_lst = value.split(",")
                for idx, item in enumerate(value_lst):
                    value_lst[idx] = value_lst[idx].strip()

            if path == "aard":
                # Get the abbreviation
                abbr = aard_abbr[str(value)]
                # Set the value
                if self == None:
                    lstQ['aard'] = abbr
                else:
                    if self.aard != abbr:
                        # Log change
                        oErr.Status("custom_add change [aard] from {} into {}".format(self.aard, abbr))
                        # Perform change
                        self.aard = abbr
                        lstQ = True
            elif path == "fotograaf" and value != "":
                # Find the photographer
                obj = Photographer.objects.filter(name=value).first()
                if obj == None:
                    obj = Photographer.objects.create(name=value)
                # Set myself
                if self == None:
                    lstQ['fotograaf'] = obj
                else:
                    if self.fotograaf != obj:
                        # Log change
                        original = "None" if self.fotograaf is None else self.fotograaf.id
                        target = "None" if obj is None else obj.id
                        oErr.Status("custom_add change [aard] from {} into {}".format(original, target))
                        # Perform change
                        self.fotograaf = obj                
                        lstQ = True
            elif path == "locatie":
                name = oWerkstuk.get('locatie')
                land = oWerkstuk.get('land')
                plaats = oWerkstuk.get('plaats')
                x_coordinaat = oWerkstuk.get('x-coördinaat')
                y_coordinaat = oWerkstuk.get('y-coördinaat')
                # Find the Location entry - create country and/or city on-the-fly, if needed
                country = Country.objects.filter(name__iexact=land).first()
                if country is None and not land is None and land != "":
                    # Create the country
                    country = Country.objects.create(name=land)
                city = City.objects.filter(name__iexact=plaats, country=country).first()
                if city is None and not plaats is None and plaats != "":
                    # Create the city
                    city = City.objects.create(name=plaats, country=country)
                obj = Location.objects.filter(name__iexact=name, country=country, city=city).first()
                if obj == None:
                    obj = Location.objects.create(name=name, country=country, city=city, 
                                                  x_coordinaat=x_coordinaat, y_coordinaat=y_coordinaat)
                # Set myself
                if self == None:
                    lstQ['locatie'] = obj
                else:
                    if self.locatie != obj:
                        # Log change
                        original = "None" if self.locatie is None else self.locatie.id
                        target = "None" if obj is None else obj.id
                        oErr.Status("custom_add change [aard] from {} into {}".format(original, target))
                        # Perform change
                        self.locatie = obj
                        lstQ = True
            elif path == "soort":
                soort = oWerkstuk.get("soort")
                soort_eng = oWerkstuk.get("soort_engels")
                # Find the Soort entry
                obj = Soort.objects.filter(naam__iexact=soort, eng__iexact=soort_eng).first()
                if obj == None:
                    obj = Soort.objects.create(naam=soort, eng=soort_eng)
                # Set myself
                if self == None:
                    lstQ['soort'] = obj
                else:
                    if self.soort != obj:
                        # Log change
                        original = "None" if self.soort is None else self.soort.id
                        target = "None" if obj is None else obj.id
                        oErr.Status("custom_add change [aard] from {} into {}".format(original, target))
                        # Perform change
                        self.soort = obj
                        lstQ = True
            elif path == "materiaal":
                # Only three choices recognized
                materiaal = oWerkstuk.get("materiaal")
                abbr = materiaal_abbr[materiaal.lower()]
                # Set the value
                if self == None:
                    lstQ['materiaal'] = abbr
                else:
                    if self.materiaal != abbr:
                        # Log change
                        oErr.Status("custom_add change [materiaal] from {} into {}".format(self.materiaal, abbr))
                        # Perform change
                        self.materiaal = abbr
                        lstQ = True

                # Find the materiaal entry
            else:
                # Figure out what to do in this case
                pass

        except:
            msg = oErr.get_error_message()
            oErr.DoError("Werkstuk/custom_set")
            lstQ = {} if self is None else False
        return lstQ

    def custom_tags(oWerkstuk, addonly = False, taglist = None, deleting = [], adding = []):
        """Get the tags from oWerkstuk and update"""

        oErr = ErrHandle()
        bFound = True
        try:
            if taglist == None:
                taglist = [{"id": x.id, "name": x.name, "field": x.field} for x in Tag.objects.all()]
            accessid = oWerkstuk['objectid']
            obj = Werkstuk.objects.filter(accessid=accessid).first()
            if obj != None:
                # Walk all tags
                for oTag in taglist:
                    # tagvalue = oWerkstuk[oTag['name'].lower()]
                    tagvalue = oWerkstuk[oTag['field']]
                    if isinstance(tagvalue, int):
                        tagvalue = str(tagvalue)
                    if tagvalue == "True" or tagvalue == "1":
                        # see if it is there
                        wtag = WerkstukTag.objects.filter(werkstuk=obj, tag_id=oTag['id']).first()
                        if wtag == None:
                            # Add this relation
                            # WerkstukTag.objects.create(werkstuk=obj, tag_id=oTag['id'])
                            adding.append(dict(werkstuk_id=obj.id, tag_id=oTag['id']))
                    else:
                        # If the relation exists, it must be removed
                        wtag = WerkstukTag.objects.filter(werkstuk=obj, tag_id=oTag['id']).first()
                        if wtag != None:
                            # wtag.delete()
                            deleting.append(dict(werkstuk_id=obj.id, tag_id=oTag['id']))
        except:
            msg = oErr.get_error_message()
            oErr.DoError("custom_tags")
            bFound = False
        return bFound

    def get_aard(self, language):
        """Get aard either in Dutch or in English"""
        sBack = ""
        obj = FieldChoice.objects.filter(field=AARD_TYPE, abbr=self.aard).first()
        if obj != None:
            if language == "nl":
                # Get dutch
                sBack = obj.dutch_name
            else:
                sBack = obj.english_name
        return sBack

    def get_beschrijving(self, language):
        """Get description either in Dutch or in English"""
        sBack = ""
        if language == "nl":
            # Get dutch
            sBack = self.beschrijving_nl
        else:
            sBack = self.beschrijving_en
        # Make sure the description is shown in a larger font
        sBack = "<div class='werkstuk-beschrijving'>{}</div>".format(sBack)
        return sBack

    def get_daterange(self):
        lhtml = []
        sBack = ""
        if self.begindatum != None:
            # There is a start date, but what about the ending date?
            if self.einddatum != None and self.einddatum != self.begindatum:
                # Both a start and end date
                sBack = "{}-{}".format(self.begindatum, self.einddatum)
            else:
                # Only start date
                sBack = "{}".format(self.begindatum)
        elif self.einddatum != None:
            # Only finishing date
            sBack = "{}".format(self.einddatum)
        return sBack

    def get_iconclasscodes(self):
        sBack = ""
        lhtml = []
        for obj in self.iconclasses.all().order_by('notatie'):
            lhtml.append(obj.notatie)
        sBack = ", ".join(lhtml)
        return sBack

    def get_image_html(self, language, field="inventarisnummer", tooltip=None):
        """Get the HTML <img> code for this one"""

        oErr = ErrHandle()
        sBack = ""
        sTitle = ""

        try:
            # Get the number of the image, depending on the options
            sImageName = "{}".format(getattr(self, field)) 
            # Correct for case sensitivity
            if sImageName.lower() == "ga":
                sImageName = "GA"

            # Don't show GA images
            if sImageName == "GA":
                return None, None

            # Determine the directory
            arDir = ["static", "seeker", "images"]
            if sImageName != "GA":
                arDir.append(sImageName[0:2])
            arDir.append(sImageName)
            # Combine into static image location
            image = "/{}.jpg".format( "/".join(arDir) 
                                     )
            # Create what we should return
            field_bijschrift =""
            sTitle = ""
            if field in self.afbeeldingen:
                field_bijschrift = self.afbeeldingen[field]
            if field_bijschrift != "":
                sTitle =  getattr(self, field_bijschrift)    # self.vis_bijschrift1

            if sTitle == None:
                sTitle = self.beschrijving_nl if language == "nl" else self.beschrijving_en
            descr = "object {}: {}".format(self.inventarisnummer, sImageName)

            sClass = "stalla-image" # Was: col-md-12

            if tooltip == None:
                sBack = "<img src='{}' alt='{}' class='{}' >".format(image, descr, sClass)
            else:
                sBack = "<img src='{}' alt='{}' data-toggle='tooltip' data-tooltip='werkstuk-hover' title='{}' class='{}'>".format(
                    image, descr, tooltip, sClass)

        except:
            msg = oErr.get_error_message()
            oErr.DoError("Werkstuk/get_image_html")
        return sBack, sTitle

    def get_available(self, base_name = None):
        """Make a list of images available for this item"""

        oErr = ErrHandle()
        lBack = []
        try:
            if base_name == None:
                for field, v in self.afbeeldingen.items():
                    sImageName = "{}".format(getattr(self, field)) 
                    if sImageName != "GA":
                        # This must be a picture
                        lBack.append(field)
            else:
                # Build 5 on basename
                for number in range(1,5):
                    field = "{}{}".format(base_name, number)
                    sImageName = "{}".format(getattr(self, field)) 
                    if sImageName != "GA":
                        # This must be a picture
                        lBack.append(field)

        except:
            msg = oErr.get_error_message()
            oErr.DoError("Werkstuk/get_available")
        return lBack

    def get_fotograaf(self):
        sBack = ""
        obj = self.fotograaf
        if obj == None:
            sBack = "-"
        else:
            sBack = obj.name
        return sBack

    def get_kunstenaren(self):
        sBack = "onbekend"
        lhtml = []
        for obj in self.kunstenaren.all().order_by('name'):
            lhtml.append(obj.name)
        sBack = ", ".join(lhtml)
        return sBack

    def get_lit_paralel(self):
        """Retrieve field [lit_paralel] and do some processing on it"""

        sBack = ""
        if self.lit_paralel != None and self.lit_paralel != "":
            sBack = self.lit_paralel.replace("_x000D_", "<br />")
        return sBack

    def get_locatie(self, as_object = False):
        sBack = ""
        lhtml = []
        oErr = ErrHandle()
        try:
            oItem = dict(country="", city="", location="")
            obj = self.locatie
            if obj != None:
                # Get the city
                city = obj.city
                if city is None:
                    plaats = "onbekend"
                    land = "onbekend"
                    if not obj.country is None:
                        land = obj.country.name
                else:
                    plaats = city.name
                    # Get the country
                    country = city.country
                    if country is None:
                        land = "onbekend"
                    else:
                        land = country.name
                if as_object:
                    oItem['country'] = land
                    oItem['city'] = plaats
                    oItem['location'] = obj.name
                    sBack = json.dumps(oItem)
                else:
                    sBack = "{}, {}: {}".format(land, plaats, obj.name)
        except:
            msg = oErr.get_error_message()
            oErr.DoError("Werkstuk/get_locatie")
        return sBack

    def get_soort(self, language):
        sBack = ""
        if language == "nl":
            sBack = self.soort.naam
        else:
            sBack = self.soort.eng
        return sBack

    def get_tags_html(self, language):
        lhtml = []
        sort_field = "name" if language == "nl" else "eng"
        for obj in self.tags.all().order_by(sort_field):
            sTag = "<span class='badge categorie'>{}</span>".format( getattr(obj, sort_field))
            lhtml.append(sTag)
        sBack = " ".join(lhtml)
        return sBack

    def read_excel(oStatus, fname):
        """Update information from Excel file"""

        oErr = ErrHandle()
        oResult = {}
        count = 0
        lst_all = ["object", "iconclass", "Kunstenaar", "literatuur", "tags",
                    "iconclassnotatie", "Kunstenaarnotatie", "literatuurverwijzing"]
        lst_skip = ["object", "iconclass", "Kunstenaar", "literatuur",
                    "iconclassnotatie", "Kunstenaarnotatie", "literatuurverwijzing"]

        try:
            # Check
            if not os.path.exists(fname) or not os.path.isfile(fname):
                # Return negatively
                oErr.Status("Werkstuk/read_excel: cannot read {}".format(fname))
                oResult['status'] = "error"
                oResult['msg'] = "Werkstuk/read_excel: cannot read {}".format(fname)
                return oResult

            # Pre-load taglist
            taglist = [{"id": x.id, "name": x.name} for x in Tag.objects.all()]

            # (1) Read the 'object' table with new werkstukken
            if "object" not in lst_skip:
                count = 0
                for oRow in excel_generator(fname, wsName="object"):
                    # Show where we are
                    count += 1
                    oStatus.set("reading object {}".format(count))
                    # Process this item into the database
                    custom_add(oRow, Werkstuk, "objectid")

            # (2) Read the 'iconclass' objects
            if "iconclass" not in lst_skip:
                count = 0
                bAddOnly = (IconClass.objects.count() == 0)
                for oRow in excel_generator(fname, wsName="iconclass"):
                    # Show where we are
                    count += 1
                    oStatus.set("reading iconclass {}".format(count))
                    # Process this item into the database
                    custom_add(oRow, IconClass, "iconclassID")

            # (3) Read the 'Kunstenaar' objects
            if "Kunstenaar" not in lst_skip:
                count = 0
                bAddOnly = (Kunstenaar.objects.count() == 0)
                for oRow in excel_generator(fname, wsName="Kunstenaar"):
                    # Show where we are
                    count += 1
                    oStatus.set("reading kunstenaar {}".format(count))
                    # Process this item into the database
                    custom_add(oRow, Kunstenaar, "KunstenaarID")

            # (4) Read the 'literatuur' objects
            if "literatuur" not in lst_skip:
                count = 0
                bAddOnly = (Literatuur.objects.count() == 0)
                for oRow in excel_generator(fname, wsName="literatuur"):
                    # Show where we are
                    count += 1
                    oStatus.set("reading literatuur {}".format(count))
                    # Process this item into the database
                    custom_add(oRow, Literatuur, "literatuurID")

            # Update many-to-many relations
            if "tags" not in lst_skip:
                count = 0
                addonly = (WerkstukTag.objects.count() == 0)
                with transaction.atomic():
                    for oRow in excel_generator(fname, wsName="object"):
                        # Show where we are
                        count += 1
                        if count % 1000 == 0:
                            oStatus.set("reading tag {}".format(count))
                        oErr.Status("reading tag {}".format(count))
                        # Process this item into the database
                        Werkstuk.custom_tags(oRow, addonly=addonly, taglist=taglist)

            # (2) Read the 'iconclassnotatie' objects
            oErr.Status("Looking at: iconclassnotatie")
            if "iconclassnotatie" not in lst_skip:
                count = 0
                bAddOnly = (Iconclassnotatie.objects.count() == 0)
                for oRow in excel_generator(fname, wsName="iconclassnotatie"):
                    # Show where we are
                    count += 1
                    if count % 1000 == 0:
                        oStatus.set("reading Iconclassnotatie {}".format(count))
                    # Process this item into the database
                    if oRow['objectid'] != "" and oRow['iconclassid'] != "":
                        custom_add(oRow, Iconclassnotatie, "iconobjid")

            # (3) Read the 'Kunstenaarnotatie' objects
            oErr.Status("Looking at: Kunstenaarnotatie")
            if "Kunstenaarnotatie" not in lst_skip:
                count = 0
                bAddOnly = (Kunstenaarnotatie.objects.count() == 0)
                for oRow in excel_generator(fname, wsName="Kunstenaarnotatie"):
                    # Show where we are
                    count += 1
                    if count % 1000 == 0:
                        oStatus.set("reading Kunstenaarnotatie {}".format(count))
                    # Process this item into the database
                    if oRow['objectid'] != "" and oRow['kunstenaarid'] != "":
                        custom_add(oRow, Kunstenaarnotatie, "kunstenaarobjid")

            # (4) Read the 'literatuurverwijzing' objects
            oErr.Status("Looking at: literatuurverwijzing")
            if "literatuurverwijzing" not in lst_skip:
                count = 0
                bAddOnly = (Literatuurverwijzing.objects.count() == 0)
                with transaction.atomic():
                    for oRow in excel_generator(fname, wsName="literatuurverwijzing"):
                        # Show where we are
                        count += 1
                        if count % 1000 == 0:
                            oStatus.set("reading Literatuurverwijzing {}".format(count))
                        # Process this item into the database
                        if oRow['objectid'] != "" and oRow['literatuurid'] != "":
                            custom_add(oRow, Literatuurverwijzing, "litobjectid", addonly = bAddOnly)

            # Now we are ready
            oResult['status'] = "ok"
            oResult['msg'] = "Read {} items".format(count)
            oResult['count'] = count
            # Log finish of this 
            oErr.Status("Finished reading: {} item(s)".format(count))
        except:
            oResult['status'] = "error"
            oResult['msg'] = oErr.get_error_message()

        # Return the correct result
        return oResult
            
    def read_json(oStatus, data=None, fname=None):
        """Update information from JSON file"""

        def get_object_dict(oStallaData, tblname, f_target, f_m2m, extra_fields = None):
            """"""

            oErr = ErrHandle()
            oList = []
            oDict = {}
            try:
                for oRow in oStallaData[tblname]:
                    # Within each access table, the Access own id is called ObjectID
                    objectid = oRow.get("objectid", "")
                    # The targetid is the access id within the target table
                    targetid = oRow.get(f_target, "")
                    # The m2m id is the access id of the 
                    m2m_id = oRow.get(f_m2m)
                    oItem = dict(accessid=m2m_id, targetid=targetid)

                    # Possibly add extra fields
                    if not extra_fields is None:
                        for extra in extra_fields:
                            value = oRow.get(extra)
                            if not value is None:
                                oItem[extra] = value

                    if objectid != "" and targetid != "":
                        if objectid in oDict:
                            oDict[objectid].append(oItem)
                        else:
                            oDict[objectid] = [ oItem ]
                # Turn dict into a list
                oList = [{'objectid': k, 'values': v} for k, v in oDict.items()]
            except:
                msg = oErr.get_error_message()
                oErr.DoError("get_object_dict")
            return oList

        oErr = ErrHandle()
        oResult = {}
        oBack = {}
        count = 0
        lst_all = ["object", "iconclass", "Kunstenaar", "literatuur", "tags",
                    "iconclassnotatie", "Kunstenaarnotatie", "literatuurverwijzing"]
        lst_skip = []
        oStallaData = {}
        skip_start = False

        try:
            # Starting test: the number of WerkstukTag
            count_wst = WerkstukTag.objects.count()

            if data is None:
                if not fname is None:
                    # Check
                    if not os.path.exists(fname) or not os.path.isfile(fname):
                        # Return negatively
                        oErr.Status("Werkstuk/read_json: cannot read {}".format(fname))
                        oResult['status'] = "error"
                        oResult['msg'] = "Werkstuk/read_json: cannot read {}".format(fname)
                        return oResult

                    # Read the JSON data into an object
                    with open(fname, "r", encoding="utf-8") as fp:
                        oStallaData = json.load(fp)
            else:
                oStallaData = data

            # We are saving this file
            oBack['file'] = "loaded JSON"
            oStatus.set("loaded", oBack)

            # Pre-load taglist
            taglist = [{"id": x.id, "name": x.name, "field": x.field} for x in Tag.objects.all()]

            # (1) Read the 'object' table with new werkstukken
            oStatus.set("tables 1", {'table': 'object'})
            if "object" not in lst_skip:
                count = 0
                # Read the 
                with transaction.atomic():
                    for oRow in oStallaData['object']:
                        # Show where we are
                        count += 1
                        oStatus.set("reading object {}".format(count))
                        # Process this item into the database
                        custom_add(oRow, Werkstuk, "objectid")

            # (2) Read the 'iconclass' objects
            oStatus.set("tables 2", {'table': 'iconclass'})
            if "iconclass" not in lst_skip:
                count = 0
                bAddOnly = (IconClass.objects.count() == 0)
                with transaction.atomic():
                    for oRow in oStallaData['iconclass']:
                        # Show where we are
                        count += 1
                        oStatus.set("reading iconclass {}".format(count))
                        # Process this item into the database
                        custom_add(oRow, IconClass, "iconclassID")

            # (3) Read the 'Kunstenaar' objects
            oStatus.set("tables 3", {'table': 'Kunstenaar'})
            if "Kunstenaar" not in lst_skip:
                count = 0
                bAddOnly = (Kunstenaar.objects.count() == 0)
                with transaction.atomic():
                    for oRow in oStallaData['Kunstenaar']:
                        # Show where we are
                        count += 1
                        oStatus.set("reading kunstenaar {}".format(count))
                        # Process this item into the database
                        custom_add(oRow, Kunstenaar, "KunstenaarID")

            # (4) Read the 'literatuur' objects
            oStatus.set("tables 4", {'table': 'literatuur'})
            if "literatuur" not in lst_skip:
                count = 0
                bAddOnly = (Literatuur.objects.count() == 0)
                with transaction.atomic():
                    for oRow in oStallaData['literatuur']:
                        # Show where we are
                        count += 1
                        oStatus.set("reading literatuur {}".format(count))
                        # Process this item into the database
                        custom_add(oRow, Literatuur, "literatuurID")

            # Update many-to-many relations

            # (1) the Tags per object
            oStatus.set("tables 5", {'table': 'tags'})
            if "tags" not in lst_skip:
                count = 0
                addonly = (WerkstukTag.objects.count() == 0)
                wt_adding = []
                wt_deleting = []
                for oRow in oStallaData['object']:
                    # Show where we are
                    count += 1
                    if count % 1000 == 0:
                        oStatus.set("reading tag {}".format(count))
                        oErr.Status("reading tag {}".format(count))
                    # Process this item into the database
                    Werkstuk.custom_tags(oRow, addonly=addonly, taglist=taglist, deleting=wt_deleting, adding=wt_adding)
                    count_wst_now = WerkstukTag.objects.count()
                    if count_wst_now < count_wst:
                        # Did something go wrong?
                        iStop = True
                # Do the adding
                oStatus.set("Adding tags: {}".format(len(wt_adding)))
                with transaction.atomic():
                    for oItem in wt_adding:
                        werkstuk_id = oItem['werkstuk_id']
                        tag_id = oItem['tag_id']
                        WerkstukTag.objects.create(werkstuk_id=werkstuk_id, tag_id=tag_id)
                # Do any deleting
                oStatus.set("Deleting tags: {}".format(len(wt_deleting)))
                with transaction.atomic():
                    for oItem in wt_deleting:
                        werkstuk_id = oItem['werkstuk_id']
                        tag_id = oItem['tag_id']
                        WerkstukTag.objects.filter(werkstuk_id=werkstuk_id, tag_id=tag_id).delete()

            # (2) Read the 'iconclassnotatie' objects
            oStatus.set("tables 6", {'table': 'iconclassnotatie'})
            if "iconclassnotatie" not in lst_skip:
                count = 0
                bAddOnly = (Iconclassnotatie.objects.count() == 0)
                if bAddOnly:
                    with transaction.atomic():
                        for oRow in oStallaData['iconclassnotatie']:
                            # Show where we are
                            count += 1
                            if count % 1000 == 0:
                                oStatus.set("reading Iconclassnotatie {}".format(count))
                            # Process this item into the database
                            objectid = oRow.get("objectid", "")
                            iconclassid = oRow.get("iconclassid", "")
                            if objectid != "" and iconclassid != "":
                                custom_add(oRow, Iconclassnotatie, "iconobjid")
                else:
                    # Transform the iconclassnotatie lines
                    oList = get_object_dict(oStallaData, "iconclassnotatie", "iconclassid", "iconobjid")

                    # Walk the list of target values per Werkstuk object
                    count = 0
                    for oRow in oList:
                        # Show where we are 
                        count += 1
                        if count % 1000 == 0:
                            oStatus.set("reading Iconclassnotatie {}".format(count))

                        # Process the new m2m list
                        Werkstuk.custom_m2m(oRow, IconClass, Iconclassnotatie, "werkstuk_iconclass", "iconclass")

            # (3) Read the 'Kunstenaarnotatie' objects
            oStatus.set("tables 7", {'table': 'Kunstenaarnotatie'})
            if "Kunstenaarnotatie" not in lst_skip:
                count = 0
                bAddOnly = (Kunstenaarnotatie.objects.count() == 0)
                if bAddOnly:
                    with transaction.atomic():
                        for oRow in oStallaData['Kunstenaarnotatie']:
                            # Show where we are
                            count += 1
                            if count % 1000 == 0:
                                oStatus.set("reading Kunstenaarnotatie {}".format(count))
                            # Process this item into the database
                            objectid = oRow.get("objectid", "")
                            kunstenaarid = oRow.get("kunstenaarid", "")
                            if objectid != "" and kunstenaarid != "":
                                custom_add(oRow, Kunstenaarnotatie, "kunstenaarobjid")
                else:
                    # Transform the kunstenaarnotatie lines
                    oList = get_object_dict(oStallaData, "Kunstenaarnotatie", "kunstenaarid", "kunstenaarobjid")

                    # Walk the list of target values per Werkstuk object
                    count = 0
                    for oRow in oList:
                        # Show where we are 
                        count += 1
                        if count % 1000 == 0:
                            oStatus.set("reading Kunstenaarnotatie {}".format(count))

                        # Process the new m2m list
                        Werkstuk.custom_m2m(oRow, Kunstenaar, Kunstenaarnotatie, "werkstuk_kunstenaar", "kunstenaar")


            # (4) Read the 'literatuurverwijzing' objects
            oStatus.set("tables 8", {'table': 'literatuurverwijzing'})
            if "literatuurverwijzing" not in lst_skip:
                count = 0
                bAddOnly = (Literatuurverwijzing.objects.count() == 0)
                if bAddOnly:
                    with transaction.atomic():
                        for oRow in oStallaData['literatuurverwijzing']:
                            # Show where we are
                            count += 1
                            if count % 1000 == 0:
                                oStatus.set("reading literatuurverwijzing {}".format(count))
                            # Process this item into the database
                            objectid = oRow.get("objectid", "")
                            literatuurid = oRow.get("literatuurid", "")
                            if objectid != "" and literatuurid != "":
                                custom_add(oRow, Literatuurverwijzing, "litobjectid", addonly = bAddOnly)
                else:
                    # Transform the iconclassnotatie lines
                    oList = get_object_dict(oStallaData, "literatuurverwijzing", "literatuurid", "litobjectid",
                                            extra_fields = ['paginaverwijzing', 'exemplaar'])

                    # Walk the list of target values per Werkstuk object
                    count = 0
                    for oRow in oList:
                        # Show where we are 
                        count += 1
                        if count % 1000 == 0:
                            oStatus.set("reading Literatuurverwijzing {}".format(count))

                        # Process the new m2m list
                        Werkstuk.custom_m2m(oRow, Literatuur, Literatuurverwijzing, "werkstuk_literatuur", "literatuur",
                                            extra_fields = ['paginaverwijzing', 'exemplaar'])

            # Update the SOORT table
            soort_ids = []
            with transaction.atomic():
                for obj in Werkstuk.objects.all():
                   if not obj.soort.id in soort_ids:
                       soort_ids.append(obj.soort.id)
            # Get all the Soort elements that are not actually used in Werkstuk
            remove_ids = [x.id for x in Soort.objects.exclude(id__in=soort_ids)]
            if len(remove_ids) > 0:
                # Remove those soort elements altogether
                Soort.objects.filter(id__in=remove_ids).delete()
                # Tell what we have done
                oStatus.set("soort: removed {} unused items".format(len(remove_ids)))


            # Now we are ready
            oResult['status'] = "ok"
            oResult['msg'] = "Read {} items".format(count)
            oResult['count'] = count
        except:
            oResult['status'] = "error"
            oResult['msg'] = oErr.get_error_message()

        # Return the correct result
        return oResult


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

    # [1] Take over the access ID
    accessid = models.IntegerField("Access ID")
    # [1] THe link to the werkstuk
    werkstuk = models.ForeignKey(Werkstuk, on_delete=models.CASCADE, related_name="werkstuk_iconclass")
    # [1] THe link to the iconclass
    iconclass = models.ForeignKey(IconClass, on_delete=models.CASCADE, related_name="werkstuk_iconclass")
    # [0-1] Remark on this link
    opmerking = models.CharField("Remark", max_length=MAX_TEXT_LEN, blank=True, null=True)

    # Scheme for downloading and uploading
    specification = [
        # Note: name=Excel file, path=Db field name
        {'name': 'iconobjID',   'type': 'field',    'path': 'accessid'},
        {'name': 'iconclassID', 'type': 'func',     'path': 'iconclass'},
        {'name': 'objectID',    'type': 'func',     'path': 'werkstuk'},
        {'name': 'opmerking'},
        ]

    def custom_get(self, path, **kwargs):
        sBack = ""
        oErr = ErrHandle()
        try:
            profile = kwargs.get("profile")
            username = kwargs.get("username")
            team_group = kwargs.get("team_group")

            # Specific path handling
            if path == "iconclass":
                sBack = self.iconclass.accessid
            elif path == "werkstuk":
                sBack = self.werkstuk.accessid

        except:
            msg = oErr.get_error_message()
            oErr.DoError("Iconclassnotatie/custom_get")
        return sBack

    def custom_set(self, path, value, oWerkstuk, **kwargs):
        """Set related items"""

        oErr = ErrHandle()
        lstQ = {}
        try:
            profile = kwargs.get("profile")
            username = kwargs.get("username")
            team_group = kwargs.get("team_group")

            value_lst = []
            if isinstance(value, str) and value[0] != '[':
                value_lst = value.split(",")
                for idx, item in enumerate(value_lst):
                    value_lst[idx] = value_lst[idx].strip()

            # Specific path handling
            if path == "iconclass":
                # Get the correct IconClass object
                iconclass = IconClass.objects.filter(accessid=value).first()
                # Set the value
                if self == None:
                    lstQ['iconclass'] = iconclass
                else:
                    if self.iconclass != iconclass:
                        self.iconclass = iconclass
                    else:
                        lstQ = False

            elif path == "werkstuk":
                # Get the correct IconClass object
                werkstuk = Werkstuk.objects.filter(accessid=value).first()
                # Set the value
                if self == None:
                    lstQ['werkstuk'] = werkstuk
                else:
                    if self.werkstuk != werkstuk:
                        self.werkstuk = werkstuk
                    else:
                        lstQ = False

            else:
                # Figure out what to do in this case
                pass

        except:
            msg = oErr.get_error_message()
            oErr.DoError("Iconclassnotatie/custom_set")
            lstQ = None
        return lstQ


class Kunstenaarnotatie(models.Model):
    """Link between werkstuk and tag"""

    # [1] Take over the access ID
    accessid = models.IntegerField("Access ID")
    # [1] THe link to the werkstuk
    werkstuk = models.ForeignKey(Werkstuk, on_delete=models.CASCADE, related_name="werkstuk_kunstenaar")
    # [1] THe link to the artist
    kunstenaar = models.ForeignKey(Kunstenaar, on_delete=models.CASCADE, related_name="werkstuk_kunstenaar")
    # [1] And a date: the date of saving this relation
    created = models.DateTimeField(default=get_current_datetime)

    # Scheme for downloading and uploading
    specification = [
        # Note: name=Excel file, path=Db field name
        {'name': 'KunstenaarobjID', 'type': 'field',    'path': 'accessid'},
        {'name': 'KunstenaarID',    'type': 'func',     'path': 'kunstenaar'},
        {'name': 'objectID',        'type': 'func',     'path': 'werkstuk'},
        ]

    def custom_get(self, path, **kwargs):
        sBack = ""
        oErr = ErrHandle()
        try:
            profile = kwargs.get("profile")
            username = kwargs.get("username")
            team_group = kwargs.get("team_group")

            # Specific path handling
            if path == "kunstenaar":
                sBack = self.kunstenaar.accessid
            elif path == "werkstuk":
                sBack = self.werkstuk.accessid

        except:
            msg = oErr.get_error_message()
            oErr.DoError("Kunstenaarnotatie/custom_get")
        return sBack

    def custom_set(self, path, value, oWerkstuk, **kwargs):
        """Set related items"""

        oErr = ErrHandle()
        lstQ = {}
        try:
            profile = kwargs.get("profile")
            username = kwargs.get("username")
            team_group = kwargs.get("team_group")

            value_lst = []
            if isinstance(value, str) and value[0] != '[':
                value_lst = value.split(",")
                for idx, item in enumerate(value_lst):
                    value_lst[idx] = value_lst[idx].strip()

            # Specific path handling
            if path == "kunstenaar":
                # Get the correct Kunstenaar object
                kunstenaar = Kunstenaar.objects.filter(accessid=value).first()
                # Set the value
                if self == None:
                    lstQ['kunstenaar'] = kunstenaar
                else:
                    if self.kunstenaar != kunstenaar:
                        self.kunstenaar = kunstenaar
                    else:
                        lstQ = False

            elif path == "werkstuk":
                # Get the correct IconClass object
                werkstuk = Werkstuk.objects.filter(accessid=value).first()
                # Set the value
                if self == None:
                    lstQ['werkstuk'] = werkstuk
                else:
                    if self.werkstuk != werkstuk:
                        self.werkstuk = werkstuk
                    else:
                        lstQ = False

            else:
                # Figure out what to do in this case
                pass

        except:
            msg = oErr.get_error_message()
            oErr.DoError("Kunstenaarnotatie/custom_set")
            lstQ = None
        return lstQ


class Literatuurverwijzing(models.Model):
    """Link between literatuur and werkstuk"""

    # [1] Take over the access ID
    accessid = models.IntegerField("Access ID")
    # [1] THe link to the werkstuk
    werkstuk = models.ForeignKey(Werkstuk, on_delete=models.CASCADE, related_name="werkstuk_literatuur")
    # [1] THe link to the literature
    literatuur = models.ForeignKey(Literatuur, on_delete=models.CASCADE, related_name="werkstuk_literatuur")
    # [0-1] Page reference
    paginaverwijzing = models.CharField("Page reference", max_length=MAX_TEXT_LEN, blank=True, null=True)
    # [1] Whether an item of this literature is in possession or not
    exemplaar = models.BooleanField(default=False) 
    # [0-1] ROom for a remark
    opmerking = models.TextField("Opmerking", blank=True, null=True)

    # Scheme for downloading and uploading
    specification = [
        # Note: name=Excel file, path=Db field name
        {'name': 'litobjectID',     'type': 'field',    'path': 'accessid'},
        {'name': 'literatuurID',    'type': 'func',     'path': 'literatuur'},
        {'name': 'objectID',        'type': 'func',     'path': 'werkstuk'},
        {'name': 'paginaverwijzing'},
        {'name': 'exemplaar'},
        {'name': 'opmerking'},
        ]

    def custom_get(self, path, **kwargs):
        sBack = ""
        oErr = ErrHandle()
        try:
            profile = kwargs.get("profile")
            username = kwargs.get("username")
            team_group = kwargs.get("team_group")

            # Specific path handling
            if path == "literatuur":
                sBack = self.literatuur.accessid
            elif path == "werkstuk":
                sBack = self.werkstuk.accessid

        except:
            msg = oErr.get_error_message()
            oErr.DoError("Literatuurverwijzing/custom_get")
        return sBack

    def custom_set(self, path, value, oWerkstuk, **kwargs):
        """Set related items"""

        oErr = ErrHandle()
        lstQ = {}
        try:
            profile = kwargs.get("profile")
            username = kwargs.get("username")
            team_group = kwargs.get("team_group")

            value_lst = []
            if isinstance(value, str) and value[0] != '[':
                value_lst = value.split(",")
                for idx, item in enumerate(value_lst):
                    value_lst[idx] = value_lst[idx].strip()

            # Specific path handling
            if path == "literatuur":
                # Get the correct IconClass object
                literatuur = Literatuur.objects.filter(accessid=value).first()
                # Set the value
                if self == None:
                    lstQ['literatuur'] = literatuur
                else:
                    if self.literatuur != literatuur:
                        self.literatuur = literatuur
                    else:
                        lstQ = False

            elif path == "werkstuk":
                # Get the correct IconClass object
                werkstuk = Werkstuk.objects.filter(accessid=value).first()
                # Set the value
                if self == None:
                    lstQ['werkstuk'] = werkstuk
                else:
                    if self.werkstuk != werkstuk:
                        self.werkstuk = werkstuk
                    else:
                        lstQ = False

            else:
                # Figure out what to do in this case
                pass

        except:
            msg = oErr.get_error_message()
            oErr.DoError("Literatuurverwijzing/custom_set")
            lstQ = None
        return lstQ




