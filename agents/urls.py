from django.urls import path
from . import views

urlpatterns = [
    path("ajax/all-locations/",views.all_locations, name="all_locations"),
    path("ajax/agents/", views.search_agents, name="search_agents"),
]