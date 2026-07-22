from django.urls import path
from . import views
urlpatterns = [
    path('invite-a-neighbor/', views.add_customer, name='add_customer'),
    path('upload-profile-image/', views.upload_profile_image, name='upload_profile_image'),
]
   