import re
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Note


def sanitize_html(html_content):
    """Allow only safe inline formatting tags to prevent XSS."""
    if not html_content:
        return ''
    # Allow only these tags
    allowed_tags = {'b', 'i', 'u', 'strong', 'em', 'br', 'p', 'div'}
    # Remove all tags except allowed ones
    def replace_tag(match):
        tag = match.group(1).strip().split()[0].strip('/').lower()
        if tag in allowed_tags:
            return match.group(0)
        return ''
    result = re.sub(r'<(/?\s*[a-zA-Z][a-zA-Z0-9]*[^>]*)>', replace_tag, html_content)
    return result


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
    share_url = None
    if note.is_shared and note.share_token:
        from django.urls import reverse
        share_url = request.build_absolute_uri(reverse('shared_note', args=[note.share_token]))
    return render(request, 'notes/note_detail.html', {'note': note, 'share_url': share_url})


@login_required
def note_create(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        body = sanitize_html(request.POST.get('body', ''))
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
        note.body = sanitize_html(request.POST.get('body', ''))
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
