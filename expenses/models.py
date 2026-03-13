from datetime import timedelta
from django.db import models
from django.contrib.auth.models import User


class Expense(models.Model):
    CATEGORY_CHOICES = [
        ('food', 'Food & Dining'),
        ('transport', 'Transport'),
        ('shopping', 'Shopping'),
        ('bills', 'Bills & Utilities'),
        ('entertainment', 'Entertainment'),
        ('health', 'Health'),
        ('education', 'Education'),
        ('other', 'Other'),
    ]

    RECURRENCE_CHOICES = [
        ('none', 'One-time'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    date = models.DateField()
    note = models.TextField(blank=True)
    recurrence = models.CharField(max_length=10, choices=RECURRENCE_CHOICES, default='none')
    is_recurring_parent = models.BooleanField(default=False)
    parent_expense = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='recurring_children')
    next_due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.title} - {self.amount}"

    def calculate_next_due(self, from_date):
        if self.recurrence == 'daily':
            return from_date + timedelta(days=1)
        elif self.recurrence == 'weekly':
            return from_date + timedelta(weeks=1)
        elif self.recurrence == 'monthly':
            month = from_date.month + 1
            year = from_date.year
            if month > 12:
                month = 1
                year += 1
            day = min(from_date.day, 28)
            return from_date.replace(year=year, month=month, day=day)
        elif self.recurrence == 'yearly':
            return from_date.replace(year=from_date.year + 1)
        return None


class BudgetSetting(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='budget_setting')
    monthly_limit = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.user.username} - Budget: {self.monthly_limit}"
