from django.urls import path
from . import views

app_name = 'MoeList'
urlpatterns = [
    path('', views.index, name='index'),
    path('indexPart/<int:year>', views.index_part, name='index_part'),
    path('update/<str:name>/<int:value>/', views.update_variables, name='update_variables'),
    path('<int:anilist_id>/', views.anime, name='anime'),
    path('<int:anilist_id>/ep/<int:ep>', views.episodes, name='episode'),
    path('<int:anilist_id>/ep/<int:ep>/watchedPart', views.watched_part, name='watched_part'),
    path('watchedAll/<int:anilist_id>/', views.anime_watched_all, name='watched_all'),
    path('reloadInfo/<int:anilist_id>/', views.reload_info, name='reload_info'),
    path('options/<str:key>/<str:value>', views.update_options, name='update_options'),
    path('search', views.search_pp, name='search'),
    path('ajaxSearch', views.ajax_search, name='ajax_search'),
    path('delete/', views.delete_anime, name='delete'),
    path('open', views.open_file, name='open'),
    path('filepath/', views.filepath, name='filepath'),
    path('filedelete/', views.trash_file, name='fileDelete'),
    path('file_handler/', views.file_handler, name='file_handler'),
    path('<int:anilist_id>/downloadableEp', views.get_downloadable_ep_http, name='animeDownloadableEp'),
    path('<int:anilist_id>/downloadableEpRefresh', views.get_downloadable_ep_http_refresh, name='animeDownloadableEpRefresh'),
    path('kwikLinkFromSession', views.get_kwik_link_from_session, name='kwikLinkFromSession'),
    path('kwikDownload/<str:link>', views.get_download_link_from_kwik, name='kwikDownload'),
    path('importMAL', views.import_mal, name='importMAL'),
    path('settings', views.settings, name='settings'),
    path('settingsHandler', views.settings_handler, name='settingsHandler'),
]
