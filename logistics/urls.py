from django.urls import path
from . import views

urlpatterns = [
    path("book-parcel/", views.book_parcel, name="book_parcel"),
    path("dispatch/customer/<int:customer_id>/", views.dispatch_customer_orders, name="dispatch_customer_orders"),
    path("dispatch/sent/<int:dispatch_id>/", views.mark_dispatch_sent, name="mark_dispatch_sent"),
    path("dispatches", views.all_dispatch_orders, name="all_dispatch_orders"),
    path("order-dispatch_detail/<int:dispatch_id>/", views.order_dispatch_detail, name="order_dispatch_detail"),

    path('parcel-summary-details/<int:dispatch_id>', views.parcel_summary_details, name='parcel_summary_details'),
    path('receipt/<int:pk>/', views.parcel_receipt_view, name='parcel_receipt'),

    path('agent-dispatch-list', views.agent_dispatch_list, name='agent_dispatch_list'),
    path('agent-dispatch-detail/<int:pk>', views.agent_dispatch_detail, name='agent_dispatch_detail'),
    path('package-dispatch-detail/<int:pk>', views.package_dispatch_detail, name='package_dispatch_detail'),
    path('package-dispatch-list', views.package_dispatch_list, name='package_dispatch_list'),

    path('customer-received-packages', views.customer_received_packages, name='customer_received_packages'),
    path('customer-send-packages', views.customer_send_packages, name='customer_send_packages'),
]