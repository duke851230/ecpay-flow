from django.urls import path
from .views import index, payment_result

urlpatterns = [
    path('', index, name='index'),
    path('payment_result/', payment_result, name='payment_result'),
]