from django.urls import path

from . import views
app_name = 'Browser'
urlpatterns = [
    path('', views.index, name='index'),
    path('file_methods', views.file_methods, name='file_methods'),
    path('check_file_name', views.check_file_name, name='check_file_name')
]
