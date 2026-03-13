import csv
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q
from django.http import HttpResponse
from .models import Expense, BudgetSetting


@login_required
def expense_dashboard(request):
    user_expenses = Expense.objects.filter(user=request.user)
    today = date.today()
    this_month_expenses = user_expenses.filter(date__year=today.year, date__month=today.month)
    monthly_spending = this_month_expenses.aggregate(total=Sum('amount'))['total'] or 0
    total_spending = user_expenses.aggregate(total=Sum('amount'))['total'] or 0
    expense_count = user_expenses.count()
    recent_expenses = user_expenses[:5]

    # Top category this month
    top_category = None
    category_colors = {
        'food': 'orange', 'transport': 'blue', 'shopping': 'pink',
        'bills': 'purple', 'entertainment': 'cyan', 'health': 'green',
        'education': 'blue', 'other': 'muted',
    }
    category_data = []
    if this_month_expenses.exists():
        cat_totals = {}
        for exp in this_month_expenses:
            cat_totals[exp.category] = cat_totals.get(exp.category, 0) + float(exp.amount)
        if cat_totals:
            total_cat = sum(cat_totals.values())
            top_category = dict(Expense.CATEGORY_CHOICES).get(max(cat_totals, key=cat_totals.get))
            for cat_key, cat_amount in cat_totals.items():
                category_data.append({
                    'label': dict(Expense.CATEGORY_CHOICES).get(cat_key, cat_key),
                    'amount': cat_amount,
                    'percentage': round((cat_amount / total_cat) * 100) if total_cat else 0,
                    'color': category_colors.get(cat_key, 'blue'),
                })
            category_data.sort(key=lambda x: x['amount'], reverse=True)

    # Build conic gradient string for donut chart
    conic_stops = []
    running = 0
    for item in category_data:
        start = running
        end = running + item['percentage']
        conic_stops.append(f"var(--accent-{item['color']}) {start}% {end}%")
        running = end
    conic_gradient = ', '.join(conic_stops) if conic_stops else 'var(--text-muted) 0% 100%'

    # Budget
    budget_limit = 0
    budget_percentage = 0
    try:
        budget = request.user.budget_setting
        budget_limit = budget.monthly_limit
        if budget_limit > 0:
            budget_percentage = min(round((float(monthly_spending) / float(budget_limit)) * 100), 100)
    except BudgetSetting.DoesNotExist:
        pass

    return render(request, 'expenses/expense_dashboard.html', {
        'monthly_spending': monthly_spending,
        'total_spending': total_spending,
        'expense_count': expense_count,
        'recent_expenses': recent_expenses,
        'top_category': top_category,
        'current_month': today.strftime('%B %Y'),
        'category_data': category_data,
        'budget_limit': budget_limit,
        'budget_percentage': budget_percentage,
        'conic_gradient': conic_gradient,
    })


def generate_recurring_expenses(user):
    today = date.today()
    parents = Expense.objects.filter(
        user=user, is_recurring_parent=True, next_due_date__lte=today
    )
    for parent in parents:
        while parent.next_due_date and parent.next_due_date <= today:
            Expense.objects.create(
                user=user,
                title=parent.title,
                amount=parent.amount,
                category=parent.category,
                date=parent.next_due_date,
                note=parent.note,
                recurrence='none',
                parent_expense=parent,
            )
            parent.next_due_date = parent.calculate_next_due(parent.next_due_date)
            parent.save()


@login_required
def expense_list(request):
    generate_recurring_expenses(request.user)

    expenses = Expense.objects.filter(user=request.user)
    category = request.GET.get('category', '')
    month = request.GET.get('month', '')
    query = request.GET.get('q', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    if query:
        expenses = expenses.filter(Q(title__icontains=query) | Q(note__icontains=query))
    if category:
        expenses = expenses.filter(category=category)
    if month:
        year, m = month.split('-')
        expenses = expenses.filter(date__year=int(year), date__month=int(m))
    if date_from:
        expenses = expenses.filter(date__gte=date_from)
    if date_to:
        expenses = expenses.filter(date__lte=date_to)

    total = expenses.aggregate(total=Sum('amount'))['total'] or 0

    # Budget
    budget_limit = 0
    budget_percentage = 0
    today = date.today()
    monthly_total = Expense.objects.filter(
        user=request.user, date__year=today.year, date__month=today.month
    ).aggregate(total=Sum('amount'))['total'] or 0
    try:
        budget = request.user.budget_setting
        budget_limit = budget.monthly_limit
        if budget_limit > 0:
            budget_percentage = min(round((float(monthly_total) / float(budget_limit)) * 100), 100)
    except BudgetSetting.DoesNotExist:
        pass

    return render(request, 'expenses/expense_list.html', {
        'expenses': expenses,
        'total': total,
        'selected_category': category,
        'selected_month': month,
        'query': query,
        'date_from': date_from,
        'date_to': date_to,
        'categories': Expense.CATEGORY_CHOICES,
        'budget_limit': budget_limit,
        'budget_percentage': budget_percentage,
        'monthly_total': monthly_total,
    })


@login_required
def expense_summary(request):
    expenses = Expense.objects.filter(user=request.user)
    today = date.today()

    this_month = expenses.filter(date__year=today.year, date__month=today.month)
    monthly_total = this_month.aggregate(total=Sum('amount'))['total'] or 0
    overall_total = expenses.aggregate(total=Sum('amount'))['total'] or 0

    category_totals = {}
    for cat_key, cat_label in Expense.CATEGORY_CHOICES:
        cat_sum = expenses.filter(category=cat_key).aggregate(total=Sum('amount'))['total'] or 0
        if cat_sum > 0:
            category_totals[cat_label] = cat_sum

    recent = expenses[:5]

    return render(request, 'expenses/expense_summary.html', {
        'monthly_total': monthly_total,
        'overall_total': overall_total,
        'category_totals': category_totals,
        'total_count': expenses.count(),
        'recent': recent,
        'current_month': today.strftime('%B %Y'),
    })


@login_required
def expense_create(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        amount = request.POST.get('amount')
        category = request.POST.get('category', 'other')
        expense_date = request.POST.get('date')
        note = request.POST.get('note', '')
        recurrence = request.POST.get('recurrence', 'none')
        if title and amount and expense_date:
            expense = Expense.objects.create(
                user=request.user,
                title=title,
                amount=amount,
                category=category,
                date=expense_date,
                note=note,
                recurrence=recurrence,
            )
            if recurrence != 'none':
                expense.is_recurring_parent = True
                expense.next_due_date = expense.calculate_next_due(expense.date)
                expense.save()
            messages.success(request, 'Expense added successfully!')
            return redirect('expense_list')
    return render(request, 'expenses/expense_form.html', {
        'categories': Expense.CATEGORY_CHOICES,
        'recurrence_choices': Expense.RECURRENCE_CHOICES,
        'today': date.today().isoformat(),
    })


@login_required
def expense_edit(request, pk):
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    if request.method == 'POST':
        expense.title = request.POST.get('title')
        expense.amount = request.POST.get('amount')
        expense.category = request.POST.get('category', expense.category)
        expense.date = request.POST.get('date')
        expense.note = request.POST.get('note', '')
        recurrence = request.POST.get('recurrence', 'none')
        expense.recurrence = recurrence
        if recurrence != 'none':
            expense.is_recurring_parent = True
            expense.next_due_date = expense.calculate_next_due(expense.date)
        else:
            expense.is_recurring_parent = False
            expense.next_due_date = None
        if expense.title and expense.amount and expense.date:
            expense.save()
            messages.success(request, 'Expense updated successfully!')
            return redirect('expense_list')
    return render(request, 'expenses/expense_form.html', {
        'expense': expense,
        'categories': Expense.CATEGORY_CHOICES,
        'recurrence_choices': Expense.RECURRENCE_CHOICES,
    })


@login_required
def expense_delete(request, pk):
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    if request.method == 'POST':
        expense.delete()
        messages.success(request, 'Expense deleted successfully!')
        return redirect('expense_list')
    return render(request, 'expenses/expense_confirm_delete.html', {'expense': expense})


@login_required
def expense_export_csv(request):
    expenses = Expense.objects.filter(user=request.user)

    query = request.GET.get('q', '')
    category = request.GET.get('category', '')
    month = request.GET.get('month', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    if query:
        expenses = expenses.filter(Q(title__icontains=query) | Q(note__icontains=query))
    if category:
        expenses = expenses.filter(category=category)
    if month:
        year, m = month.split('-')
        expenses = expenses.filter(date__year=int(year), date__month=int(m))
    if date_from:
        expenses = expenses.filter(date__gte=date_from)
    if date_to:
        expenses = expenses.filter(date__lte=date_to)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="expenses.csv"'
    writer = csv.writer(response)
    writer.writerow(['Title', 'Amount', 'Category', 'Date', 'Note'])
    for exp in expenses:
        writer.writerow([exp.title, exp.amount, exp.get_category_display(), exp.date, exp.note])
    return response


@login_required
def set_budget(request):
    if request.method == 'POST':
        limit = request.POST.get('monthly_limit', 0)
        budget, _ = BudgetSetting.objects.get_or_create(user=request.user)
        budget.monthly_limit = limit
        budget.save()
        messages.success(request, 'Budget updated!')
    return redirect(request.META.get('HTTP_REFERER', 'expense_list'))
