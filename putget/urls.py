from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('put', views.put, name='put'),
    path('get', views.get, name='get'),
]