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
    path("ajax/get-customer-points/", views.get_customer_credits, name="get_customer_credits"),
    path("ajax/pay-using-points/", views.pay_using_credit, name="pay_using_credits"),
    path("ajax/use-free-reward/", views.use_free_reward, name="use_free_reward"),

    #
]