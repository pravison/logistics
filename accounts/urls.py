from django.urls import path
from . import views
urlpatterns = [
    path('register-user/', views.register_user, name='register_user'),
    path('login-user/', views.login_user, name='login_user'),
    path('logout-user/', views.logout_user, name='logout_user'),

    path('request-reset-code/', views.request_reset_code, name='request_reset_code'),
    path('verify-reset-code/', views.verify_reset_code, name='verify_reset_code'),
    path('reset-password/', views.reset_password, name='reset_password'),
    ]
   