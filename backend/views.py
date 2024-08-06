import json
import hashlib
import datetime

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http.request import HttpRequest
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.urls import reverse
from django.conf import settings

from .models import Order


def _generate_check_mac_value(order_id: str, amount: str) -> str:
    """ 這是我自己寫的方式。

    因為我不太確定 ECPAY 除了用 HashKey 和 HashIV 外，還用了哪些參數來組成 check_mac_value。
    故這邊只先用 OrderID 和 Amount 來實現。
    """
    key: str = settings.ECPAY_HASH_KEY
    iv: str = settings.ECPAY_HASH_IV

    raw: str = f'HashKey={key}&OrderID={order_id}&Amount={amount}&HashIV={iv}'
    check_mac_value: str = hashlib.sha256(raw.encode('utf-8')).hexdigest().upper()

    return check_mac_value

class CreateOrderView(View):
    def post(self, request: HttpRequest) -> HttpResponse:
        request_body: str = request.body.decode('utf-8')
        payload: dict = json.loads(request_body)
        print(f"CreateOrderView's {payload=}")

        amount: int = payload.get('amount')
        order_id: str = "order{now_timestamp}".format(
            now_timestamp=int(datetime.datetime.now().timestamp())
        )

        try:
            order: Order = Order.objects.create(order_id=order_id, amount=amount)
            return JsonResponse(
                {'order_id': order.order_id, 'amount': order.amount}, status=201
            )
        except Exception as e:
            print(str(e))
            return HttpResponse(str(e), status=400)

class ProcessPaymentView(View):
    def post(self, request: HttpRequest, order_id: str) -> HttpResponse:
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
        parameters['CheckMacValue'] = _generate_check_mac_value(order.order_id, order.amount)
        
        # 返回支付表單數據
        return JsonResponse({'parameters': parameters, 'endpoint': endpoint}, status=200)

class PaymentCallbackView(View):
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request: HttpRequest) -> HttpResponse:
        data: dict = request.POST.dict()
        print(f"payment_callback's {data=}")

        received_check_mac_value = data.get('CheckMacValue')
        order_id: str = data.get('MerchantTradeNo')
        amount: str = data.get('TradeAmt')
        generated_check_mac_value = _generate_check_mac_value(order_id, amount)

        print(f"In payment_callback, {received_check_mac_value=}, {generated_check_mac_value=}")

        if received_check_mac_value == generated_check_mac_value:
            return HttpResponse("1|OK")
        else:
            raise Exception("Mac Value Error!!")

