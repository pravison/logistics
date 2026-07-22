from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Customer(models.Model):
    user = models.OneToOneField(User, blank=True, null=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=250, default='customer')
    profile_image = models.ImageField(upload_to='customer-profiles', null=True, blank=True)
    phone_number = models.CharField(max_length=25, null=True, blank=True)
    delivery_address = models.TextField(blank=True, null=True)
    total_loyalty_points = models.IntegerField(default=0)
    total_available_votes = models.IntegerField(default=10, help_text='this are vote slots that will be used to cast votes for others')
    refferal_code = models.CharField(max_length=8, unique=True)
    reffered_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE, help_text='user who reffered customer', related_name='reffer')
    date_joined = models.DateTimeField(auto_now_add = True)
    date_updated = models.DateTimeField(auto_now = True)
    def __str__(self):
        name = f'{self.user.first_name} {self.user.last_name}' if self.user else self.name
        return f'{name }'
    @property
    def imageUrl(self):
        try:
            url= self.profile_image.url
        except:
            url = ''
        return url

    
class ScanCount(models.Model):
    customer = models.ForeignKey(Customer, blank=True, null=True, on_delete=models.SET_NULL)
    number = models.IntegerField()
    date_scanned = models.DateField(auto_now_add=True)
    def __str__(self):
        return f'{self.business} - {self.number}'

    
