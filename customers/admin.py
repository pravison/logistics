from django.contrib import admin
from .models import Customer, ScanCount

# Register your models here.
admin.site.register(Customer)

admin.site.register(ScanCount)