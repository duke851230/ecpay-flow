from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt


def index(request):
    return render(request, 'index.html')

@csrf_exempt
def payment_result(request):
    if request.method == 'POST':
        data = request.POST
        return render(request, 'payment_result.html', {'data': data})