from django.urls import path
from .views import IndexView, payment_result

urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('payment_result/', payment_result, name='payment_result'),
]