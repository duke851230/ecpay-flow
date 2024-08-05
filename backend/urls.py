from django.urls import path
from .views import CreateOrderView, ProcessPaymentView, payment_callback

urlpatterns = [
    path('create_order/', CreateOrderView.as_view(), name='create_order'),
    path('process_payment/<str:order_id>/', ProcessPaymentView.as_view(), name='process_payment'),
    path('payment_callback/', payment_callback, name='payment_callback'),
]