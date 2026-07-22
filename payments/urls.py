from django.urls import path
from . import views
urlpatterns = [
    path('mpesa-stk-push/', views.mpesa_stk_push, name='mpesa_stk_push'),
    path('mpesa-payment/status/<str:checkout_id>/', views.mpesa_payment_status, name='mpesa_payment_status'),
    path('payment_callback/', views.mpesa_payment_callback, name='mpesa_payment_callback'),
    # walet payment
    path("wallet-payment/", views.wallet_payment, name="wallet_payment"),
    # cron job url
    path("cron/sync-accounting/", views.sync_accounting_view, name="sync_accounting_view"),

    # points
    path("ajax/get-customer-points/", views.get_customer_points, name="get_customer_points"),
    path("ajax/pay-using-points/", views.pay_using_points, name="pay_using_points"),

    #
]