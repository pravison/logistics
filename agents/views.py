from django.shortcuts import render

# Create your views here.
from django.http import JsonResponse
from .models import Location, Agent

from django.http import JsonResponse

def all_locations(request):

    locations = Location.objects.select_related("county")

    results = [
        {
            "id": location.id,
            "name": location.name,
            "county": location.county_id,
        }
        for location in locations
    ]

    return JsonResponse({"results": results})

def search_agents(request):
    location = request.GET.get("location")
    q = request.GET.get("q", "")

    agents = Agent.objects.filter(
        location_id=location,
        shop_name__icontains=q
    )[:20]

    results = [
        {
            "id": agent.id,
            "text": f'{agent.shop_name} located {agent.shop_address}'
        }
        for agent in agents
    ]

    return JsonResponse({"results": results})