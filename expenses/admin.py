from django.contrib import admin
from .models import Expense, BudgetSetting

admin.site.register(Expense)
admin.site.register(BudgetSetting)
