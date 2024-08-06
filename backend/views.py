import json
import hashlib
import datetime
import collections
import urllib.parse  

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http.request import HttpRequest
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.urls import reverse
from django.conf import settings

from .models import Order


def _generate_check_mac_value(parameters: dict) -> str:
    """
    這邊是去參考 Python ecpay sdk 的 generate_check_value 函數。
    - https://github.com/ECPay/ECPayAIO_Python/blob/master/sdk/ecpay_payment_sdk.py
    """
    encrypt_type: int = int(parameters.get('EncryptType', 1))

    ordered_params: dict = collections.OrderedDict(
        sorted(parameters.items(), key=lambda k: k[0].lower())
    )
    raw: str = '&'.join([f'{k}={v}' for k, v in ordered_params.items()])
    raw = f'HashKey={settings.ECPAY_HASH_KEY}&{raw}&HashIV={settings.ECPAY_HASH_IV}'

    safe_characters: str = '-_.!*()'
    encoding_str: str = urllib.parse.quote_plus(str(raw), safe=safe_characters).lower()

    check_mac_value: str = ''
    if encrypt_type == 1:
        check_mac_value = hashlib.sha256(
            encoding_str.encode('utf-8')).hexdigest().upper()
    elif encrypt_type == 0:
        check_mac_value = hashlib.md5(
            encoding_str.encode('utf-8')).hexdigest().upper()

    return check_mac_value

class CreateOrderView(View):
    """
    這邊為了方便，只紀錄總金額，並進到創建訂單步驟。
    """
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
        order: Order = Order.objects.get(order_id=order_id)
        merchant_id: str = settings.ECPAY_MERCHANT_ID
        endpoint: str = 'https://payment-stage.ecpay.com.tw/Cashier/AioCheckOut/V5'
        # request.build_absolute_uri 會自動根據當前的 Domain 幫我組出 URL
        return_url: str = request.build_absolute_uri(reverse('payment_callback'))
        order_result_url: str = request.build_absolute_uri(reverse('payment_result'))
        print(f"ProcessPaymentView's {return_url=} {order_result_url=}")
        
        # 綠界金流的基本參數（GPT 給的，比 SDK 給的範例少很多參數，之後真的要用可能要參考技術文件）
        parameters = {
            'MerchantID': merchant_id,
            'MerchantTradeNo': order.order_id,
            'MerchantTradeDate': datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S'),
            'PaymentType': 'aio',  # All in one 的方式
            'TotalAmount': order.amount,
            'TradeDesc': 'Test Order',
            'ItemName': 'Test Item',
            'ReturnURL': return_url,
            'OrderResultURL': order_result_url,
            'ClientBackURL': order_result_url,
            'ChoosePayment': 'ALL',
            'EncryptType': 1,  # 使用 sha256
        }
        parameters['CheckMacValue'] = _generate_check_mac_value(parameters)

        return JsonResponse(
            {'parameters': parameters, 'endpoint': endpoint}, 
            status=200
        )

class PaymentCallbackView(View):
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request: HttpRequest) -> HttpResponse:
        data: dict = request.POST.dict()
        print(f"payment_callback's {data=}")

        received_check_mac_value: str = data.pop('CheckMacValue', None)
        params_to_validate: dict = {
            'MerchantID': data.get('MerchantID'),
            'MerchantTradeNo': data.get('MerchantTradeNo'),
            'PaymentDate': data.get('PaymentDate'),
            'PaymentType': data.get('PaymentType'),
            'PaymentTypeChargeFee': data.get('PaymentTypeChargeFee'),
            'RtnCode': data.get('RtnCode'),
            'RtnMsg': data.get('RtnMsg'),
            'SimulatePaid': data.get('SimulatePaid'),
            'TradeAmt': data.get('TradeAmt'),
            'TradeDate': data.get('TradeDate'),
            'TradeNo': data.get('TradeNo'),
        }

        generated_check_mac_value: str = _generate_check_mac_value(params_to_validate)

        print(f"In payment_callback, {received_check_mac_value=}, {generated_check_mac_value=}")

        if received_check_mac_value == generated_check_mac_value:
            return HttpResponse("1|OK")
        else:
            return HttpResponse("CheckMacValue Error", status=400)

