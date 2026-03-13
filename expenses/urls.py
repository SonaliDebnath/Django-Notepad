from django.urls import path
from . import views

urlpatterns = [
    path('', views.expense_list, name='expense_list'),
    path('dashboard/', views.expense_dashboard, name='expense_dashboard'),
    path('summary/', views.expense_summary, name='expense_summary'),
    path('new/', views.expense_create, name='expense_create'),
    path('export/', views.expense_export_csv, name='expense_export_csv'),
    path('budget/', views.set_budget, name='set_budget'),
    path('<int:pk>/edit/', views.expense_edit, name='expense_edit'),
    path('<int:pk>/delete/', views.expense_delete, name='expense_delete'),
]
