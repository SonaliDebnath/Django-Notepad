import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from datetime import date
from .models import Note
from expenses.models import Expense, BudgetSetting


@login_required
def dashboard(request):
    user_notes = Note.objects.filter(user=request.user)
    total = user_notes.count()
    pinned = user_notes.filter(pinned=True).count()
    recent = user_notes.order_by('-updated_at')[:5]
    colors = {}
    for note in user_notes:
        colors[note.color_tag] = colors.get(note.color_tag, 0) + 1

    # Expense stats
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

    return render(request, 'notes/dashboard.html', {
        'total': total,
        'pinned': pinned,
        'recent': recent,
        'colors': colors,
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


@login_required
def note_list(request):
    query = request.GET.get('q', '')
    user_notes = Note.objects.filter(user=request.user)
    if query:
        pinned_notes = user_notes.filter(pinned=True, title__icontains=query).order_by('-updated_at')
        notes = user_notes.filter(pinned=False, title__icontains=query).order_by('-updated_at')
    else:
        pinned_notes = user_notes.filter(pinned=True).order_by('-updated_at')
        notes = user_notes.filter(pinned=False).order_by('-updated_at')
    total = pinned_notes.count() + notes.count()
    return render(request, 'notes/note_list.html', {
        'notes': notes,
        'pinned_notes': pinned_notes,
        'query': query,
        'total': total,
    })


@login_required
def note_detail(request, pk):
    note = get_object_or_404(Note, pk=pk, user=request.user)
    share_url = None
    if note.is_shared and note.share_token:
        share_url = request.build_absolute_uri(f'/shared/{note.share_token}/')
    return render(request, 'notes/note_detail.html', {'note': note, 'share_url': share_url})


@login_required
def note_create(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        body = request.POST.get('body')
        color_tag = request.POST.get('color_tag', 'blue')
        if title and body:
            Note.objects.create(user=request.user, title=title, body=body, color_tag=color_tag)
            messages.success(request, 'Note created successfully!')
            return redirect('note_list')
    return render(request, 'notes/note_form.html')


@login_required
def note_edit(request, pk):
    note = get_object_or_404(Note, pk=pk, user=request.user)
    if request.method == 'POST':
        note.title = request.POST.get('title')
        note.body = request.POST.get('body')
        note.color_tag = request.POST.get('color_tag', note.color_tag)
        if note.title and note.body:
            note.save()
            messages.success(request, 'Note updated successfully!')
            return redirect('note_list')
    return render(request, 'notes/note_form.html', {'note': note})


@login_required
def note_delete(request, pk):
    note = get_object_or_404(Note, pk=pk, user=request.user)
    if request.method == 'POST':
        note.delete()
        messages.success(request, 'Note deleted successfully!')
        return redirect('note_list')
    return render(request, 'notes/note_confirm_delete.html', {'note': note})


@login_required
def note_toggle_pin(request, pk):
    note = get_object_or_404(Note, pk=pk, user=request.user)
    if request.method == 'POST':
        note.pinned = not note.pinned
        note.save()
        messages.success(request, f'Note {"pinned" if note.pinned else "unpinned"}!')
    return redirect('note_list')


@login_required
def note_toggle_share(request, pk):
    note = get_object_or_404(Note, pk=pk, user=request.user)
    if request.method == 'POST':
        if note.is_shared:
            note.is_shared = False
            note.share_token = None
            note.save()
            messages.success(request, 'Note is no longer shared.')
        else:
            note.is_shared = True
            note.share_token = uuid.uuid4()
            note.save()
            messages.success(request, 'Shareable link generated!')
    return redirect('note_detail', pk=note.pk)


def shared_note(request, token):
    note = get_object_or_404(Note, share_token=token, is_shared=True)
    return render(request, 'notes/shared_note.html', {'note': note})
