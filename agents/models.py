from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class County(models.Model):
    name = models.CharField(max_length=100)
    def __str__(self):
        return self.name
    
class Location(models.Model):
    county = models.ForeignKey(County, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    def __str__(self):
        return f'{self.name} in {self.county}'
    
class Agent(models.Model):
    user = models.OneToOneField(User, blank=True, null=True, on_delete=models.SET_NULL)
    shop_name = models.CharField(max_length=100)
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    shop_address = models.TextField(help_text='we are located 3rd floor travis building, next to afya centre')
    description = models.TextField(help_text='describe what your business does')
    phone_number  = models.CharField(max_length=30)
    outside_photo = models.ImageField(upload_to='shop_address_photos', null=True, blank=True)
    approved = models.BooleanField(default=False)
    def __str__(self):
        return f'{self.shop_name} located {self.location.county}, {self.location.name} location'