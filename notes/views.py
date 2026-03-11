from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Note


@login_required
def dashboard(request):
    user_notes = Note.objects.filter(user=request.user)
    total = user_notes.count()
    pinned = user_notes.filter(pinned=True).count()
    recent = user_notes.order_by('-updated_at')[:5]
    colors = {}
    for note in user_notes:
        colors[note.color_tag] = colors.get(note.color_tag, 0) + 1
    return render(request, 'notes/dashboard.html', {
        'total': total,
        'pinned': pinned,
        'recent': recent,
        'colors': colors,
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
    return render(request, 'notes/note_detail.html', {'note': note})


@login_required
def note_create(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        body = request.POST.get('body')
        color_tag = request.POST.get('color_tag', 'blue')
        if title and body:
            Note.objects.create(user=request.user, title=title, body=body, color_tag=color_tag)
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
            return redirect('note_list')
    return render(request, 'notes/note_form.html', {'note': note})


@login_required
def note_delete(request, pk):
    note = get_object_or_404(Note, pk=pk, user=request.user)
    if request.method == 'POST':
        note.delete()
        return redirect('note_list')
    return render(request, 'notes/note_confirm_delete.html', {'note': note})


@login_required
def note_toggle_pin(request, pk):
    note = get_object_or_404(Note, pk=pk, user=request.user)
    if request.method == 'POST':
        note.pinned = not note.pinned
        note.save()
    return redirect('note_list')
