from django.urls import path, re_path
from rest_framework.urlpatterns import format_suffix_patterns
from api import views

urlpatterns = [
        path('v1/vms/', views.VMList.as_view()),
        path('v1/hosts/', views.HostList.as_view()),
        re_path('v1/hosts/(?P<pk>.*)/', views.HostDetail.as_view()),
        path('v1/ips/', views.IPList.as_view()),
        re_path('v1/ips/(?P<pk>.*)/', views.IPDetail.as_view()),
        re_path('v1/vms/(?P<pk>.*)/', views.VMDetail.as_view()),
]

urlpatterns = format_suffix_patterns(urlpatterns)