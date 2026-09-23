from django.db import models

class RequestLog(models.Model):
    user_id = models.CharField(max_length=100, verbose_name="ID Пользователя")
    url = models.TextField(verbose_name="Запрошенный URL")
    request_type = models.CharField(max_length=20, verbose_name="Тип (PDF/Video)")
    status_code = models.IntegerField(verbose_name="Код ответа")
    execution_time = models.FloatField(verbose_name="Время выполнения (сек)")
    error_message = models.TextField(null=True, blank=True, verbose_name="Ошибка")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата/Время")

    def __str__(self):
        return f"{self.user_id} - {self.request_type} ({self.status_code})"

    class Meta:
        verbose_name = "Лог запроса"
        verbose_name_plural = "Логи запросов"



# Create your models here.
