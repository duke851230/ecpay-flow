from django.db import models

class Order(models.Model):
    order_id = models.CharField(max_length=20, unique=True)
    amount = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_paid = models.BooleanField(default=False)

    def __str__(self):
        return self.order_id