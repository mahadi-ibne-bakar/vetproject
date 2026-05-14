from django.contrib import admin
from django.urls import path
from django.http import HttpResponse
from django.template import loader


def home(request):
    template = loader.get_template('home.html')
    return HttpResponse(template.render({}, request))


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
]