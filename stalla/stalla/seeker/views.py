"""
Definition of views for the SEEKER app.
"""

from django.apps import apps
from django.contrib import admin
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import Group
from django.urls import reverse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import transaction
from django.db.models import Q, Prefetch, Count, F
from django.db.models.functions import Lower
from django.db.models.query import QuerySet 
from django.forms import formset_factory, modelformset_factory, inlineformset_factory, ValidationError
from django.forms.models import model_to_dict
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse, FileResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.template.loader import render_to_string
from django.template import Context
from django.utils.translation import gettext as _
from django.views.generic.detail import DetailView
from django.views.generic.base import RedirectView
from django.views.generic import ListView, View
from django.views.decorators.csrf import csrf_exempt

# General imports
from datetime import datetime
import fnmatch
import sys, os
import base64
import copy
import json
import csv, re

# ======= imports from my own application ======
from stalla.settings import APP_PREFIX, WRITABLE_DIR, MEDIA_DIR
from stalla.utils import ErrHandle
from stalla.seeker.forms import SignUpForm, WerkstukForm
from stalla.seeker.models import get_now_time, get_current_datetime, process_userdata, \
    User, Group, Information, Visit, NewsItem, Status, \
    Werkstuk
from stalla.seeker.adaptations import listview_adaptations

# ======= from RU-Basic ========================
from stalla.basic.views import BasicPart, BasicList, BasicDetails, make_search_list, add_rel_item, adapt_search

# Some constants that can be used
paginateSize = 20
paginateSelect = 15
paginateValues = (100, 50, 20, 10, 5, 2, 1, )

# Global debugging 
bDebug = False


def get_application_name():
    """Try to get the name of this application"""

    # Walk through all the installed apps
    for app in apps.get_app_configs():
        # Check if this is a site-package
        if "site-package" not in app.path:
            # Get the name of this app
            name = app.name
            # Take the first part before the dot
            project_name = name.split(".")[0]
            return project_name
    return "unknown"
# Provide application-specific information
PROJECT_NAME = get_application_name()
app_uploader = "{}_uploader".format(PROJECT_NAME.lower())
app_editor = "{}_editor".format(PROJECT_NAME.lower())
app_userplus = "{}_userplus".format(PROJECT_NAME.lower())
app_developer = "{}_developer".format(PROJECT_NAME.lower())
app_moderator = "{}_moderator".format(PROJECT_NAME.lower())

def get_application_context(request, context):
    context['is_app_uploader'] = user_is_ingroup(request, app_uploader)
    context['is_app_editor'] = user_is_ingroup(request, app_editor)
    context['is_app_moderator'] = user_is_superuser(request) or user_is_ingroup(request, app_moderator)
    return context

def treat_bom(sHtml):
    """REmove the BOM marker except at the beginning of the string"""

    # Check if it is in the beginning
    bStartsWithBom = sHtml.startswith(u'\ufeff')
    # Remove everywhere
    sHtml = sHtml.replace(u'\ufeff', '')
    # Return what we have
    return sHtml

def adapt_m2m(cls, instance, field1, qs, field2, extra = [], extrargs = {}, qfilter = {}, 
              related_is_through = False, userplus = None, added=None, deleted=None):
    """Adapt the 'field' of 'instance' to contain only the items in 'qs'
    
    The lists [added] and [deleted] (if specified) will contain links to the elements that have been added and deleted
    If [deleted] is specified, then the items will not be deleted by adapt_m2m(). Caller needs to do this.
    """

    errHandle = ErrHandle()
    try:
        # Get current associations
        lstQ = [Q(**{field1: instance})]
        for k,v in qfilter.items(): lstQ.append(Q(**{k: v}))
        through_qs = cls.objects.filter(*lstQ)
        if related_is_through:
            related_qs = through_qs
        else:
            related_qs = [getattr(x, field2) for x in through_qs]
        # make sure all items in [qs] are associated
        if userplus == None or userplus:
            for obj in qs:
                if obj not in related_qs:
                    # Add the association
                    args = {field1: instance}
                    if related_is_through:
                        args[field2] = getattr(obj, field2)
                    else:
                        args[field2] = obj
                    for item in extra:
                        # Copy the field with this name from [obj] to 
                        args[item] = getattr(obj, item)
                    for k,v in extrargs.items():
                        args[k] = v
                    # cls.objects.create(**{field1: instance, field2: obj})
                    new = cls.objects.create(**args)
                    if added != None:
                        added.append(new)

        # Remove from [cls] all associations that are not in [qs]
        # NOTE: do not allow userplus to delete
        for item in through_qs:
            if related_is_through:
                obj = item
            else:
                obj = getattr(item, field2)
            if obj not in qs:
                if deleted == None:
                    # Remove this item
                    item.delete()
                else:
                    deleted.append(item)
        # Return okay
        return True
    except:
        msg = errHandle.get_error_message()
        return False

def adapt_m2o(cls, instance, field, qs, link_to_obj = None, **kwargs):
    """Adapt the instances of [cls] pointing to [instance] with [field] to only include [qs] """

    errHandle = ErrHandle()
    try:
        # Get all the [cls] items currently linking to [instance]
        lstQ = [Q(**{field: instance})]
        linked_qs = cls.objects.filter(*lstQ)
        if link_to_obj != None:
            linked_through = [getattr(x, link_to_obj) for x in linked_qs]
        # make sure all items in [qs] are linked to [instance]
        for obj in qs:
            if (obj not in linked_qs) and (link_to_obj == None or obj not in linked_through):
                # Create new object
                oNew = cls()
                setattr(oNew, field, instance)
                # Copy the local fields
                for lfield in obj._meta.local_fields:
                    fname = lfield.name
                    if fname != "id" and fname != field:
                        # Copy the field value
                        setattr(oNew, fname, getattr(obj, fname))
                for k, v in kwargs.items():
                    setattr(oNew, k, v)
                # Need to add an object link?
                if link_to_obj != None:
                    setattr(oNew, link_to_obj, obj)
                oNew.save()
        # Remove links that are not in [qs]
        for obj in linked_qs:
            if obj not in qs:
                # Remove this item
                obj.delete()
        # Return okay
        return True
    except:
        msg = errHandle.get_error_message()
        return False

def adapt_m2o_sig(instance, qs):
    """Adapt the instances of [SermonSignature] pointing to [instance] to only include [qs] 
    
    Note: convert SermonSignature into (Gold) Signature
    """

    errHandle = ErrHandle()
    try:
        # Get all the [SermonSignature] items currently linking to [instance]
        linked_qs = SermonSignature.objects.filter(sermon=instance)
        # make sure all items in [qs] are linked to [instance]
        bRedo = False
        for obj in qs:
            # Get the SermonSignature equivalent for Gold signature [obj]
            sermsig = instance.get_sermonsig(obj)
            if sermsig not in linked_qs:
                # Indicate that we need to re-query
                bRedo = True
        # Do we need to re-query?
        if bRedo: 
            # Yes we do...
            linked_qs = SermonSignature.objects.filter(sermon=instance)
        # Remove links that are not in [qs]
        for obj in linked_qs:
            # Get the gold-signature equivalent of this sermon signature
            gsig = obj.get_goldsig()
            # Check if the gold-sermon equivalent is in [qs]
            if gsig not in qs:
                # Remove this item
                obj.delete()
        # Return okay
        return True
    except:
        msg = errHandle.get_error_message()
        return False

def is_empty_form(form):
    """Check if the indicated form has any cleaned_data"""

    if "cleaned_data" not in form:
        form.is_valid()
    cleaned = form.cleaned_data
    return (len(cleaned) == 0)

def user_is_authenticated(request):
    # Is this user authenticated?
    username = request.user.username
    user = User.objects.filter(username=username).first()
    response = False if user == None else user.is_authenticated
    return response

def user_is_ingroup(request, sGroup):
    # Is this user part of the indicated group?
    user = User.objects.filter(username=request.user.username).first()
    response = username_is_ingroup(user, sGroup)
    return response

def username_is_ingroup(user, sGroup):
    # glist = user.groups.values_list('name', flat=True)

    # Only look at group if the user is known
    if user == None:
        glist = []
    else:
        glist = [x.name for x in user.groups.all()]

        # Only needed for debugging
        if bDebug:
            ErrHandle().Status("User [{}] is in groups: {}".format(user, glist))
    # Evaluate the list
    bIsInGroup = (sGroup in glist)
    return bIsInGroup

def user_is_superuser(request):
    bFound = False
    # Is this user part of the indicated group?
    username = request.user.username
    if username != "":
        user = User.objects.filter(username=username).first()
        if user != None:
            bFound = user.is_superuser
    return bFound

def has_string_value(field, obj):
    response = (field != None and field in obj and obj[field] != None and obj[field] != "")
    return response

def has_list_value(field, obj):
    response = (field != None and field in obj and obj[field] != None and len(obj[field]) > 0)
    return response

def has_obj_value(field, obj):
    response = (field != None and field in obj and obj[field] != None)
    return response

def process_visit(request, name, is_menu, **kwargs):
    """Process one visit and return updated breadcrumbs"""

    username = "anonymous" if request.user == None else request.user.username
    if username != "anonymous" and request.user.username != "":
        # Add the visit
        Visit.add(username, name, request.get_full_path(), is_menu, **kwargs)
        ## Get the updated path list
        #p_list = Profile.get_stack(username)
    else:
        p_list = []
        p_list.append({'name': 'Home', 'url': reverse('home')})
    # Return the breadcrumbs
    # return json.dumps(p_list)
    return p_list

def get_breadcrumbs(request, name, is_menu, lst_crumb=[], **kwargs):
    """Process one visit and return updated breadcrumbs"""

    # Initialisations
    p_list = []
    p_list.append({'name': 'Home', 'url': reverse('home')})
    # Find out who this is
    username = "anonymous" if request.user == None else request.user.username
    if username != "anonymous" and request.user.username != "":
        # Add the visit
        currenturl = request.get_full_path()
        Visit.add(username, name, currenturl, is_menu, **kwargs)
        # Set the full path, dependent on the arguments we get
        for crumb in lst_crumb:
            if len(crumb) == 2:
                p_list.append(dict(name=crumb[0], url=crumb[1]))
            else:
                pass
        # Also add the final one
        p_list.append(dict(name=name, url=currenturl))
    # Return the breadcrumbs
    return p_list





# ================= STANDARD views =====================================

def home(request, errortype=None):
    """Renders the home page."""

    assert isinstance(request, HttpRequest)
    # Specify the template
    template_name = 'index.html'
    # Define the initial context
    context =  {'title':'RU-stalla',
                'year':get_current_datetime().year,
                'pfx': APP_PREFIX,
                'site_url': admin.site.site_url}
    context['is_app_uploader'] = user_is_ingroup(request, app_uploader)
    context['is_app_editor'] = user_is_ingroup(request, app_editor)
    context['is_app_moderator'] = user_is_superuser(request) or user_is_ingroup(request, app_moderator)

    # Process this visit
    context['breadcrumbs'] = get_breadcrumbs(request, "Home", True)

    # See if this is the result of a particular error
    if errortype != None:
        if errortype == "404":
            context['is_404'] = True

    # Check the newsitems for validity
    NewsItem.check_until()

    # Create the list of news-items
    lstQ = []
    lstQ.append(Q(status='val'))
    newsitem_list = NewsItem.objects.filter(*lstQ).order_by('-created', '-saved')
    context['newsitem_list'] = newsitem_list

    # Gather the statistics
    context['count_image'] = 0


    # Render and return the page
    return render(request, template_name, context)

def contact(request):
    """Renders the contact page."""
    assert isinstance(request, HttpRequest)
    context =  {'title':'Contact',
                'message':'Shari Boodts',
                'year':get_current_datetime().year,
                'pfx': APP_PREFIX,
                'site_url': admin.site.site_url}
    context['is_app_uploader'] = user_is_ingroup(request, app_uploader)

    # Process this visit
    context['breadcrumbs'] = get_breadcrumbs(request, "Contact", True)

    return render(request,'contact.html', context)

def about(request):
    """Renders the about page."""
    assert isinstance(request, HttpRequest)
    context =  {'title':'About',
                'message':'Radboud University stalla utility.',
                'year':get_current_datetime().year,
                'pfx': APP_PREFIX,
                'site_url': admin.site.site_url}
    context['is_app_uploader'] = user_is_ingroup(request, app_uploader)

    # Process this visit
    context['breadcrumbs'] = get_breadcrumbs(request, "About", True)

    return render(request,'about.html', context)

def nlogin(request):
    """Renders the not-logged-in page."""
    assert isinstance(request, HttpRequest)
    context =  {    'title':'Not logged in', 
                    'message':'Radboud University stalla utility.',
                    'year':get_current_datetime().year,}
    context['is_app_uploader'] = user_is_ingroup(request, app_uploader)
    return render(request,'nlogin.html', context)

# ================ OTHER VIEW HELP FUNCTIONS ============================

def sync_stalla(request):
    """-"""
    assert isinstance(request, HttpRequest)

    # Gather info
    context = {'title': 'SyncStalla',
               'message': 'Radboud University PASSIM'
               }
    template_name = 'seeker/syncstalla.html'
    context['is_app_uploader'] = user_is_ingroup(request, app_uploader)
    context['is_app_editor'] = user_is_ingroup(request, app_editor)
    context['is_app_moderator'] = user_is_superuser(request) or user_is_ingroup(request, app_moderator)
    context['is_superuser'] = user_is_superuser(request)

    # Add the information in the 'context' of the web page
    return render(request, template_name, context)

def sync_start(request):
    """Synchronize information"""

    oErr = ErrHandle()
    data = {'status': 'starting'}
    try:
        # Get the user
        username = request.user.username
        # Authentication
        if not user_is_ingroup(request, app_editor):
            return redirect('home')

        # Get the synchronization type
        get = request.GET
        synctype = ""
        force = False
        if 'synctype' in get:
            synctype = get['synctype']
        if 'force' in get:
            force = get['force']
            force = (force == "true" or force == "1" )

        if synctype == '':
            # Formulate a response
            data['status'] = 'no sync type specified'

        else:
            # Remove previous status objects for this combination of user/type
            qs = Status.objects.filter(user=username, type=synctype)
            qs.delete()

            # Create a status object for this combination of synctype/user
            oStatus = Status(user=username, type=synctype, status="preparing")
            oStatus.save()

            # Formulate a response
            data['status'] = 'done'

            # The actual synchronisation process starts here, depending on the type
            if synctype == "userdata":
                # Now perform the update
                oStatus.set("loading")

                oResult = process_userdata(oStatus)
                if oResult == None or oResult['result'] == False:
                    data['status'] = 'error'
                elif oResult != None:
                    data['count'] = oResult

    except:
        oErr.DoError("sync_start error")
        data['status'] = "error"

    # Return this response
    return JsonResponse(data)

def sync_progress(request):
    """Get the progress on the /crpp synchronisation process"""

    oErr = ErrHandle()
    data = {'status': 'preparing'}

    try:
        # Get the user
        username = request.user.username
        # Get the synchronization type
        get = request.GET
        synctype = ""
        if 'synctype' in get:
            synctype = get['synctype']

        if synctype == '':
            # Formulate a response
            data['status'] = 'error'
            data['msg'] = "no sync type specified" 

        else:
            # Formulate a response
            data['status'] = 'UNKNOWN'

            # Get the appropriate status object
            # sleep(1)
            oStatus = Status.objects.filter(user=username, type=synctype).first()

            # Check what we received
            if oStatus == None:
                # There is no status object for this type
                data['status'] = 'error'
                data['msg'] = "Cannot find status for {}/{}".format(
                    username, synctype)
            else:
                # Get the last status information
                data['status'] = oStatus.status
                data['msg'] = oStatus.msg
                data['count'] = oStatus.count

        # Return this response
        return JsonResponse(data)
    except:
        oErr.DoError("sync_start error")
        data = {'status': 'error'}

    # Return this response
    return JsonResponse(data)

def login_as_user(request, user_id):
    assert isinstance(request, HttpRequest)

    # Find out who I am
    supername = request.user.username
    super = User.objects.filter(username__iexact=supername).first()
    if super == None:
        return nlogin(request)

    # Make sure that I am superuser
    if super.is_staff and super.is_superuser:
        user = User.objects.filter(username__iexact=user_id).first()
        if user != None:
            # Perform the login
            login(request, user)
            return HttpResponseRedirect(reverse("home"))

    return home(request)

def signup(request):
    """Provide basic sign up and validation of it """

    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            # Save the form
            form.save()
            # Create the user
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password1')
            # also make sure that the user gets into the STAFF,
            #      otherwise he/she may not see the admin pages
            user = authenticate(username=username, 
                                password=raw_password,
                                is_staff=True)
            user.is_staff = True
            user.save()
            # Add user to the "stalla_user" group
            gQs = Group.objects.filter(name="stalla_user")
            if gQs.count() > 0:
                g = gQs[0]
                g.user_set.add(user)
            # Log in as the user
            login(request, user)
            return redirect('home')
    else:
        form = SignUpForm()
    return render(request, 'signup.html', {'form': form})

# ================ BASIC based views ===================================

class WerkstukEdit(BasicDetails):
    """The details of one werkstuk object"""

    model = Werkstuk
    mForm = None        # We are not using a form here!
    prefix = 'wer'
    new_button = False
    # no_delete = True
    permission = "readonly"
    mainitems = []

    def add_to_context(self, context, instance):
        """Add to the existing context"""

        oErr = ErrHandle()
        try:
            # Define the main items to show and edit
            context['mainitems'] = [
                {'type': 'plain', 'label': "Objectnummer:",     'value': instance.inventarisnummer,    },
                {'type': 'plain', 'label': "Aard:",             'value': instance.get_aard(self.language),    },
                {'type': 'plain', 'label': "Beschrijving:",     'value': instance.get_beschrijving(self.language),     },
                {'type': 'plain', 'label': "Locatie koorstal:", 'value': instance.plaats_koorbank,    },
                {'type': 'plain', 'label': "Iconclass codes:",  'value': instance.get_iconclasscodes(),    },
                {'type': 'plain', 'label': "Locatie koorstal:", 'value': instance.plaats_koorbank,    },
                {'type': 'plain', 'label': "Datuminterval:",    'value': instance.get_daterange(),    },
                {'type': 'plain', 'label': "Locatie:",          'value': instance.get_locatie(),    },
                {'type': 'plain', 'label': "Fotograaf:",        'value': instance.get_fotograaf(),    },
                {'type': 'plain', 'label': "Kunstenaar:",       'value': instance.get_kunstenaren(),    },
                {'type': 'plain', 'label': "Literaire aanduiding:", 'value': instance.lit_paralel,    },
                ]

        except:
            msg = oErr.get_error_message()
            oErr.DoError("WerkstukEdit/add_to_context")

        # Return the context we have made
        return context


class WerkstukDetails(WerkstukEdit):
    """Like Werkstuk Edit, but then html output"""
    rtype = "html"

    literature_def = [
        {'field': 'auteursvermelding',  'label': 'Auhor(s)',        'label_nl': 'Auteur(s)'},
        {'field': 'title',              'label': 'Title',           'label_nl': 'Titel'},
        {'field': 'plaatsvanuitgave',   'label': 'Plaats',          'label_nl': 'City'},
        {'field': 'jaar',               'label': 'Jaar',            'label_nl': 'Year'},
        {'field': 'tijdschrift',        'label': 'Tijdschrift',     'label_nl': 'Journal'},
        {'field': 'pagina',             'label': 'Paginaverwijzing', 'label_nl': 'Pages'},
        # {'field': '', 'label': '', 'label_nl': ''},
        ]

    def add_to_context(self, context, instance):
        response = super(WerkstukDetails, self).add_to_context(context, instance)

        oErr = ErrHandle()
        try:
            lHtml = []
            if 'after_details' in context:
                lHtml.append(context['after_details'])
            literaturen = []
            for obj in instance.literaturen.all().order_by('auteursvermelding', 'title'):
                oLiterature = {}
                label_field = "label_nl" if self.language == "nl" else "label"
                lines = []
                for oField in self.literature_def:
                    value = getattr(obj, oField['field'])
                    if value != None:
                        oLine = dict(label=oField[label_field], value=value)
                        lines.append(oLine)
                oLiterature['lines'] = lines
                literaturen.append(oLiterature)
            context['literaturen'] = literaturen
            lHtml.append(render_to_string('seeker/werkstuk_literatuur.html', context, self.request))
            context['after_details'] = "\n".join(lHtml)

        except:
            msg = oErr.get_error_message()
            oErr.DoError("WerkstukDetails/add_to_context")

        # Return the context we have made
        return context
    

class WerkstukListview(BasicList):
    """Search and list 'werkstuk' objects"""

    model = Werkstuk
    listform = WerkstukForm
    prefix = "wer"
    has_select2 = True
    order_cols = ['inventarisnummer', 'aard', 'beschrijving_nl']
    order_default = order_cols
    order_heads = []
    filters = []
    searches = []

    order_heads_nl = [
        {'name': 'Objectnummer',    'order': 'o=1', 'type': 'str', 'field': 'inventarisnummer', 'linkdetails': True},
        {'name': 'Aard',            'order': 'o=1', 'type': 'str', 'custom': 'aard', 'linkdetails': True},
        {'name': 'Beschrijving',    'order': 'o=2', 'type': 'str', 'custom': 'beschrijving', 'main': True, 'linkdetails': True},
        ]
    filters_nl = [ 
        {"name": "Objectnummer",    "id": "filter_inventarisnum",   "enabled": False},
        {"name": "Aard",            "id": "filter_aardtype",        "enabled": False},
        {"name": "Beschrijving",    "id": "filter_beschrijving",    "enabled": False}
        ]
    searches_nl = [
        {'section': '', 'filterlist': [
            {'filter': 'inventarisnum', 'dbfield': 'inventarisnummer',  'keyS': 'inventarisnummer'},
            {'filter': 'aardtype',      'dbfield': 'aard',              'keyType': 'fieldchoice', 'infield': 'abbr', 'keyList': 'aardlist' },
            {'filter': 'beschrijving',  'dbfield': 'beschrijving_nl',   'keyS': 'beschrijving_nl'}
            ]
         }
        ]
    order_heads_en = [
        {'name': 'Object number',   'order': 'o=1', 'type': 'str', 'field': 'inventarisnummer', 'linkdetails': True},
        {'name': 'Kind',            'order': 'o=1', 'type': 'str', 'custom': 'aard', 'linkdetails': True},
        {'name': 'Description',     'order': 'o=2', 'type': 'str', 'custom': 'beschrijving', 'main': True, 'linkdetails': True},
        ]
    filters_en = [ 
        {"name": "Object number",   "id": "filter_inventarisnum",   "enabled": False},
        {"name": "Kind",            "id": "filter_aardtype",        "enabled": False},
        {"name": "Description",     "id": "filter_beschrijving",    "enabled": False}
        ]
    searches_en = [
        {'section': '', 'filterlist': [
            {'filter': 'inventarisnum', 'dbfield': 'inventarisnummer',  'keyS': 'inventarisnummer'},
            {'filter': 'aardtype',      'dbfield': 'aard',              'keyType': 'fieldchoice', 'infield': 'abbr', 'keyList': 'aardlist' },
            {'filter': 'beschrijving',  'dbfield': 'beschrijving_en',   'keyS': 'beschrijving_en'}
            ]
         }
        ]

    def initializations(self):
        """Perform some initializations"""

        oErr = ErrHandle()
        try:

            # ======== One-time adaptations ==============
            listview_adaptations("werkstuk_list")

            # Make sure to set the correct language-dependent matters
            if self.language == "nl":
                self.order_heads = self.order_heads_nl
                self.filters = self.filters_nl
                self.searches = self.searches_nl
            else:
                self.order_heads = self.order_heads_en
                self.filters = self.filters_en
                self.searches = self.searches_en
        except:
            msg = oErr.get_error_message()
            oErr.DoError("WerkstukListview/initializations")

        return None

    def get_field_value(self, instance, custom):
        sBack = ""
        sTitle = ""
        oErr = ErrHandle()
        try:
            if custom == "aard":
                sBack = instance.get_aard(self.language)
            elif custom == "beschrijving":
                if self.language == "nl":
                    sBack = instance.beschrijving_nl
                else:
                    sBack = instance.beschrijving_en

        except:
            msg = oErr.get_error_message()
            oErr.DoError("WerkstukListview/get_field_value")
        return sBack, sTitle


