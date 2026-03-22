from django.contrib import admin
from .models import RequestLog

@admin.register(RequestLog)
class RequestLogAdmin(admin.ModelAdmin):
    # Какие колонки показывать в списке
    list_display = ('created_at', 'user_id', 'request_type', 'status_code', 'execution_time')
    # Фильтры справа
    list_filter = ('status_code', 'request_type')
    # Поиск по пользователю или ссылке
    search_fields = ('user_id', 'url')


# Register your models here.
