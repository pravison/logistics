from django.contrib import admin

# Register your models here.
from .models import PackageDispatch, AgentDispatch, Package

admin.site.register(AgentDispatch)
admin.site.register(PackageDispatch)
admin.site.register(Package)
