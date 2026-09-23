from django.shortcuts import render
from .models import RequestLog

def logs_list(request):
    status_filter = request.GET.get('status')
    if status_filter:
         # Достаем все записи из базы, сортируем: новые вверху
        logs = RequestLog.objects.filter(status_code=status_filter).order_by('-created_at')
    else:
        logs = RequestLog.objects.all().order_by('-created_at')

    # Отдаем эти данные в HTML-шаблон
    return render(request, 'logs/logs_list.html', {'logs': logs})

# Create your views here.
