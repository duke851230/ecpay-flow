import json
import hashlib
import datetime

from django.http.request import HttpRequest
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from django.conf import settings

from .models import Order
from .forms import OrderForm


def _generate_check_mac_value(parameters: dict) -> str:
    key: str = settings.ECPAY_HASH_KEY
    iv: str = settings.ECPAY_HASH_IV

    ordered_params: dict = sorted(parameters.items())
    print(f"{ordered_params=}")

    raw: str = '&'.join([f'{k}={v}' for k, v in ordered_params])
    raw: str = f'HashKey={key}&{raw}&HashIV={iv}'
    check_mac_value: str = hashlib.sha256(raw.encode('utf-8')).hexdigest().upper()

    return check_mac_value

class CreateOrderView(View):
    def post(self, request: HttpRequest) -> HttpResponse:
        request_body: str = request.body.decode('utf-8')
        payload: dict = json.loads(request_body)
        print(f"CreateOrderView's {payload=}")

        form = OrderForm(payload)
        if form.is_valid():
            order = form.save()
            return JsonResponse(
                {'order_id': order.order_id, 'amount': order.amount}, 
                status=201
            )
        
        return JsonResponse(form.errors, status=400)

class ProcessPaymentView(View):
    def post(self, request: HttpRequest, order_id: str):
        print(f"ProcessPaymentView's {order_id=}")
        order = Order.objects.get(order_id=order_id)
        merchant_id = settings.ECPAY_MERCHANT_ID
        endpoint = 'https://payment-stage.ecpay.com.tw/Cashier/AioCheckOut/V5'
        return_url = request.build_absolute_uri(reverse('payment_callback'))
        order_result_url = request.build_absolute_uri(reverse('payment_result'))
        print(f"ProcessPaymentView's {return_url=}")
        print(f"ProcessPaymentView's {order_result_url=}")
        
        # 綠界金流的基本參數
        parameters = {
            'MerchantID': merchant_id,
            'MerchantTradeNo': order.order_id,
            'MerchantTradeDate': datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S'),
            'PaymentType': 'aio',
            'TotalAmount': order.amount,
            'TradeDesc': 'Test Order',
            'ItemName': 'Test Item',
            'ReturnURL': return_url,
            'OrderResultURL': order_result_url,
            'ClientBackURL': order_result_url,
            'ChoosePayment': 'ALL',
            'EncryptType': 1,
        }
        
        parameters['CheckMacValue'] = _generate_check_mac_value(parameters)
        
        # 返回支付表單數據
        return JsonResponse({'parameters': parameters, 'endpoint': endpoint}, status=200)

@csrf_exempt
def payment_callback(request: HttpRequest):
    if request.method == "POST":
        data: dict = request.POST.dict()
        print(f"payment_callback's {data=}")
        received_check_mac_value = data.pop('CheckMacValue', None)
        generated_check_mac_value = _generate_check_mac_value(data)

        print(f"In payment_callback, {received_check_mac_value=}, {generated_check_mac_value=}")

        if received_check_mac_value == generated_check_mac_value:
            return HttpResponse("1|OK")
        else:
            raise Exception("Mac Value Error!!")

