from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Bounty

def bounty_detail(request, bounty_id):
    bounty = get_object_or_404(Bounty, id=bounty_id)
    return render(request, 'bounty.html', {'bounty': bounty})

@login_required
def claim_bounty(request, bounty_id):
    bounty = get_object_or_404(Bounty, id=bounty_id)

    if request.method == 'POST' and bounty.status == 'open':
        bounty.status = 'claimed'
        bounty.claimed_by = request.user
        bounty.save()
        return JsonResponse({'success': True})

    return JsonResponse({'success': False, 'message': 'Bounty cannot be claimed'}, status=400)