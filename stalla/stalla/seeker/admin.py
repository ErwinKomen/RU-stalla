from django.contrib import admin
from django.contrib.admin.models import LogEntry, DELETION
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.urls import reverse

from stalla.seeker.models import *
from stalla.seeker.forms import *
# from stalla.settings import ADMIN_SITE_URL

class FieldChoiceAdmin(admin.ModelAdmin):
    readonly_fields=['machine_value']
    list_display = ['english_name','dutch_name','abbr', 'machine_value','field']
    list_filter = ['field']

    def save_model(self, request, obj, form, change):

        if obj.machine_value == None:
            # Check out the query-set and make sure that it exists
            qs = FieldChoice.objects.filter(field=obj.field)
            if len(qs) == 0:
                # The field does not yet occur within FieldChoice
                # Future: ask user if that is what he wants (don't know how...)
                # For now: assume user wants to add a new field (e.g: wordClass)
                # NOTE: start with '0'
                obj.machine_value = 0
            else:
                # Calculate highest currently occurring value
                highest_machine_value = max([field_choice.machine_value for field_choice in qs])
                # The automatic machine value we calculate is 1 higher
                obj.machine_value= highest_machine_value+1

        obj.save()


class HelpChoiceAdmin(admin.ModelAdmin):
    list_display = ['field', 'display_name', 'help_url', 'help_html']
    list_filter = ['field']
    fields = ['field', 'display_name', 'searchable', 'help_url', 'help_html']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 1, 'class': 'mytextarea'})},
        }


class InformationAdmin(admin.ModelAdmin):
    """Information k/v pairs"""

    list_display = ['name', 'kvalue']
    fields = ['name', 'kvalue']


class NewsItemAdmin(admin.ModelAdmin):
    """Display and edit of [NewsItem] definitions"""

    list_display = ['title', 'until', 'status', 'created', 'saved' ]
    search_fields = ['title', 'status']
    fields = ['title', 'created', 'until', 'status', 'msg']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 1, 'class': 'mytextarea'})},
        }


class TagAdmin(admin.ModelAdmin):
    """Display and edit of [NewsItem] definitions"""

    list_display = ['abbr', 'name', 'eng' ]
    search_fields = ['abbr', 'name', 'eng']
    fields = ['abbr', 'name', 'eng']
    ordering = ['abbr']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 1, 'class': 'mytextarea'})},
        }



# Models that serve others
admin.site.register(FieldChoice, FieldChoiceAdmin)
admin.site.register(HelpChoice, HelpChoiceAdmin)
admin.site.register(NewsItem, NewsItemAdmin)
admin.site.register(Information, InformationAdmin)

# Models of this application
admin.site.register(Tag, TagAdmin)


