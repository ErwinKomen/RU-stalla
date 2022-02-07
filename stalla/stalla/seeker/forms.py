"""
Definition of forms.
"""

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils.translation import ugettext_lazy as _
from django.forms import ModelMultipleChoiceField, ModelChoiceField
from django.forms.widgets import *
from django.db.models import F, Case, Value, When, IntegerField
from django_select2.forms import Select2MultipleWidget, ModelSelect2MultipleWidget, ModelSelect2TagWidget, ModelSelect2Widget, HeavySelect2Widget

from stalla.seeker.models import *


def init_choices(obj, sFieldName, sSet, use_helptext=True, maybe_empty=False, bUseAbbr=False, exclude=None):
    if (obj.fields != None and sFieldName in obj.fields):
        if bUseAbbr:
            obj.fields[sFieldName].choices = build_abbr_list(sSet, maybe_empty=maybe_empty, exclude=exclude)
        else:
            obj.fields[sFieldName].choices = build_choice_list(sSet, maybe_empty=maybe_empty)
        if use_helptext:
            obj.fields[sFieldName].help_text = get_help(sSet)

def user_is_in_team(username, team_group, userplus=None):
    bResult = False
    # Validate
    if username and team_group and username != "" and team_group != "":
        # First filter on owner
        owner = Profile.get_user_profile(username)
        # Now check for permissions
        bResult = (owner.user.groups.filter(name=team_group).first() != None)
        # If the user has no permission, perhaps he is a 'userplus'?
        if not bResult and userplus:
            bResult = (owner.user.groups.filter(name=userplus).first() != None)
    return bResult

# ================= WIDGETS =====================================

class AardtypeWidget(ModelSelect2MultipleWidget):
    model = FieldChoice
    search_fields = [ 'english_name__icontains', 'dutch_name__icontains']
    sort_field = "english_name"

    def label_from_instance(self, obj):
        sName = obj.english_name if self.sort_field == "english_name" else obj.dutch_name
        return sName

    def get_queryset(self):
        return FieldChoice.objects.filter(field=AARD_TYPE).order_by(self.sort_field)


class AardtypeOneWidget(ModelSelect2Widget):
    model = FieldChoice
    search_fields = [ 'english_name__icontains', 'dutch_name__icontains']
    sort_field = "english_name"

    def label_from_instance(self, obj):
        sName = obj.english_name if self.sort_field == "english_name" else obj.dutch_name
        return sName

    def get_queryset(self):
        return FieldChoice.objects.filter(field=AARD_TYPE).order_by(self.sort_field)


class LandOneWidget(ModelSelect2Widget):
    model = Country
    search_fields = [ 'name__icontains']
    dependent_fields = {'plaats': 'countrycities'}
    # Note: k = form field, v = model field

    def label_from_instance(self, obj):
        return obj.name

    def get_queryset(self):
        qs = Country.objects.all().order_by('name').distinct()
        return qs


class LocatieOneWidget(ModelSelect2Widget):
    model = Location
    search_fields = [ 'name__icontains']
    dependent_fields = {}
    # Note: k = form field, v = model field

    def label_from_instance(self, obj):
        return "{} ({}, {})".format(obj.name, obj.city.name, obj.country.name)

    def get_queryset(self):
        qs = Location.objects.exclude(name="").order_by('name').distinct()
        return qs


class PlaatsOneWidget(ModelSelect2Widget):
    model = City
    search_fields = [ 'name__icontains']
    dependent_fields = {}
    # Note: k = form field, v = model field

    def label_from_instance(self, obj):
        return "{} ({})".format(obj.name, obj.country.name)

    def get_queryset(self):
        qs = City.objects.all().order_by('name').distinct()
        return qs


class SoortWidget(ModelSelect2MultipleWidget):
    model = Soort
    search_fields = [ 'naam__icontains', 'eng__icontains']
    sort_field = "eng"

    def label_from_instance(self, obj):
        sName = "-"
        sNameEng = "" if obj.eng is None or obj.eng == "" else obj.eng
        sNameNld = "" if obj.naam is None or obj.naam == "" else obj.naam
        if self.sort_field == "eng":
            if sNameNld == "":
                sName = sNameEng
            else:
                sName = "{} [{}]".format(sNameEng, sNameNld)
        elif sNameNld == "":
            sName = sNameEng
        else:
            sName = "{} [{}]".format(sNameNld, sNameEng)
        return sName

    def get_queryset(self):
        return Soort.objects.all().order_by(self.sort_field).distinct()


# ================= FORMS =======================================

class BootstrapAuthenticationForm(AuthenticationForm):
    """Authentication form which uses boostrap CSS."""
    username = forms.CharField(max_length=254,
                               widget=forms.TextInput({
                                   'class': 'form-control',
                                   'placeholder': 'User name'}))
    password = forms.CharField(label=_("Password"),
                               widget=forms.PasswordInput({
                                   'class': 'form-control',
                                   'placeholder':'Password'}))


class SignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=False, help_text='Optional.')
    last_name = forms.CharField(max_length=30, required=False, help_text='Optional.')
    email = forms.EmailField(max_length=254, help_text='Required. Inform a valid email address.')

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2', )


class WerkstukForm(forms.ModelForm):
    """A form to update and search in Werkstuk objects"""

    aardlist = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=AardtypeWidget(attrs={'data-placeholder': _('Select one or more nature types...'), 'style': 'width: 100%;', 'class': 'searching'}))
    aardtype    = forms.ModelChoiceField(queryset=None, required=False, 
                widget=AardtypeOneWidget(attrs={'data-placeholder': _('Select a nature type...'), 'style': 'width: 30%;', 'class': 'searching'}))
    soortlist = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=SoortWidget(attrs={'data-placeholder': _('Select one or more parts...'), 'style': 'width: 100%;', 'class': 'searching'}))
    land    = forms.ModelChoiceField(queryset=None, required=False, 
                widget=LandOneWidget(attrs={'data-placeholder': _('Select a country...'), 'style': 'width: 100%;', 'class': 'searching'}))
    plaats  = forms.ModelChoiceField(queryset=None, required=False, 
                widget=PlaatsOneWidget(attrs={'data-placeholder': _('Choose a place...'), 'style': 'width: 100%;', 'class': 'searching'}))
    date_from   = forms.IntegerField(label=_("Date start"), required = False,
                widget=forms.TextInput(attrs={'placeholder': _('Starting from...'),  'style': 'width: 100%;', 'class': 'searching'}))
    date_until  = forms.IntegerField(label=_("Date until"), required = False,
                widget=forms.TextInput(attrs={'placeholder': _('Until (including)...'),  'style': 'width: 100%;', 'class': 'searching'}))
    # OLD (see issue #15) 
    # taglist     = forms.ModelMultipleChoiceField(queryset=None, required=False, widget=forms.CheckboxSelectMultiple)
    taglist     = forms.MultipleChoiceField(required=False, widget=forms.CheckboxSelectMultiple)

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = Werkstuk
        fields = ['accessid', 'inventarisnummer', 'aard', 'beschrijving_nl', 'beschrijving_en',
                  'locatie']
        widgets={
            'accessid':         forms.TextInput(attrs={'style': 'width: 100%;', 'class': 'searching'}),
            'inventarisnummer': forms.TextInput(attrs={'style': 'width: 100%;', 'class': 'searching', 
                                                       'placeholder': _('object number')}),
            'aard':             forms.Select(attrs={'style': 'width: 100%;'}),
            'beschrijving_nl':  forms.Textarea(attrs={'rows': 1, 'cols': 40, 'style': 'height: 40px; width: 100%;', 'class': 'searching', 
                                                      'placeholder': 'Beschrijving...'}),
            'beschrijving_en':  forms.Textarea(attrs={'rows': 1, 'cols': 40, 'style': 'height: 40px; width: 100%;', 'class': 'searching', 
                                                      'placeholder': 'Description...'}),
            'locatie':          LocatieOneWidget(attrs={'data-placeholder': _('Select a location...'), 'style': 'width: 100%;', 'class': 'searching'}),
            }

    def __init__(self, *args, **kwargs):
        # Possibly handle language
        language = "en"
        if 'language' in kwargs:
            language = kwargs.pop('language')
        # Start by executing the standard handling
        super(WerkstukForm, self).__init__(*args, **kwargs)
        oErr = ErrHandle()
        try:
            # Some fields are not required
            self.fields['accessid'].required = False
            self.fields['inventarisnummer'].required = False
            self.fields['aard'].required = False
            self.fields['beschrijving_nl'].required = False
            self.fields['beschrijving_en'].required = False
            self.fields['locatie'].required = False

            # Set the dependent fields for [city]
            if self.prefix != "":
                self.fields['plaats'].widget.dependent_fields = {
                    '{}-land'.format(self.prefix): 'country'}
                self.fields['locatie'].widget.dependent_fields = {
                    '{}-land'.format(self.prefix): 'country',
                    '{}-plaats'.format(self.prefix): 'city'}

            # Determine what the appropriate sorting will be (language-dependant)
            tag_choices = []
            if language == "en":
                # English sorting
                aard_sorting = "english_name"
                soort_sorting = "eng"
                tag_choices = [(x.abbr, x.eng) for x in Tag.objects.all().order_by('name')]
            else:
                # Dutch sorting
                aard_sorting = "dutch_name"
                soort_sorting = "naam"
                tag_choices = [(x.abbr, x.name) for x in Tag.objects.all().order_by('name')]
            # Widget adjusting
            self.fields['aardlist'].widget.sort_field = aard_sorting
            self.fields['aardtype'].widget.sort_field = aard_sorting
            self.fields['soortlist'].widget.sort_field = soort_sorting

            # Initialize querysets
            self.fields['aardlist'].queryset = FieldChoice.objects.filter(field=AARD_TYPE).order_by(aard_sorting)
            self.fields['aardtype'].queryset = FieldChoice.objects.filter(field=AARD_TYPE).order_by(aard_sorting)
            self.fields['land'].queryset = Country.objects.order_by('name').distinct()
            self.fields['locatie'].queryset = Location.objects.exclude(name="").order_by('name').distinct()
            self.fields['plaats'].queryset = City.objects.order_by('name').distinct()
            self.fields['soortlist'].queryset = Soort.objects.all().order_by(soort_sorting).distinct()

            # OLD (see issue #15) 
            # self.fields['taglist'].queryset = Tag.objects.all().order_by('name')
            self.fields['taglist'].choices = tag_choices

            # Get the instance
            if 'instance' in kwargs:
                instance = kwargs['instance']
        except:
            msg = oErr.get_error_message()
            oErr.DoError("WerkstukForm-init")
        return None


