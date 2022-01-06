"""
Definition of urls for stalla.
"""

from datetime import datetime
from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path, re_path, include, reverse_lazy  #, url
from django.views.decorators.csrf import csrf_exempt

import stalla.seeker.views
import stalla.seeker.forms
from stalla.seeker.views import *
from stalla.basic.views import listhelp

# Import settings
from stalla.settings import APP_PREFIX

admin.autodiscover()


# Set admin stie information
admin.site.site_header = "Choir banks"
admin.site.site_title = "stalla Admin"

pfx = APP_PREFIX
use_testapp = False


urlpatterns = [
    path('', stalla.seeker.views.home, name='home'),
    path('contact/', stalla.seeker.views.contact, name='contact'),
    path('about/', stalla.seeker.views.about, name='about'),
    path('nlogin/', stalla.seeker.views.nlogin, name='nlogin'),

    path('api/listhelp', stalla.basic.views.listhelp, name='listhelp'),

    path('sync/stalla/', stalla.seeker.views.sync_stalla, name='sync_stalla'),
    path('sync/start/', stalla.seeker.views.sync_start, name='sync_start'),
    path('sync/progress/', stalla.seeker.views.sync_progress, name='sync_progress'),

    path('werkstuk/list', WerkstukListview.as_view(), name='werkstuk_list'),
    path('werkstuk/details/', WerkstukDetails.as_view(), name='werkstuk_details'),
    path('werkstuk/details/<int:pk>/', WerkstukDetails.as_view(), name='werkstuk_details'),
    re_path('werkstuk/edit(?:/(?P<pk>\d+))?/$', WerkstukEdit.as_view(), name='werkstuk_edit'),
    path('werkstuk/map/', csrf_exempt(WerkstukMapView.as_view()), name='werkstukmap'),

    # For working with ModelWidgets from the select2 package https://django-select2.readthedocs.io
    path('select2/', include('django_select2.urls')),

    path('definitions/', RedirectView.as_view(url='/'+pfx+'admin/'), name='definitions'),
    path('signup/', stalla.seeker.views.signup, name='signup'),

    # url(r'^login/user/(?P<user_id>\w[\w\d_]+)$', stalla.seeker.views.login_as_user, name='login_as'),

    path('login/',
         LoginView.as_view
         (  template_name='login.html',
            authentication_form=stalla.seeker.forms.BootstrapAuthenticationForm,
            extra_context= { 'title': 'Log in', 'year' : datetime.now().year, }
         ),
         name='login'),
    path('logout/', LogoutView.as_view(next_page=reverse_lazy('home')), name='logout'),

    path('admin/', admin.site.urls, name='admin_base'),
    path('i18n/', include('django.conf.urls.i18n')),
]
