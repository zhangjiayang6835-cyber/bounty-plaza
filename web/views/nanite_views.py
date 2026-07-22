from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ..models.nanite import NaniteType, NaniteProgram
from ..models.user_nanite import UserNanite, UserNaniteProgram

@login_required
def nanite_research(request):
    nanite_types = NaniteType.objects.filter(is_active=True)
    user_nanites = UserNanite.objects.filter(user=request.user)

    context = {
        'nanite_types': nanite_types,
        'user_nanites': user_nanites,
    }
    return render(request, 'nanite_research.html', context)

@login_required
def implant_nanite(request, nanite_type_id):
    nanite_type = NaniteType.objects.get(id=nanite_type_id)

    if request.method == 'POST':
        cloud_id = request.POST.get('cloud_id', 1)
        safety_threshold = request.POST.get('safety_threshold', 50)

        user_nanite = UserNanite.objects.create(
            user=request.user,
            nanite_type=nanite_type,
            cloud_id=cloud_id,
            safety_threshold=safety_threshold,
            research_points=0,
            is_active=True
        )

        messages.success(request, f'Successfully implanted {nanite_type.name} nanites.')
        return redirect('nanite_research')

    context = {
        'nanite_type': nanite_type,
    }
    return render(request, 'nanite_implant.html', context)

@login_required
def program_nanite(request, user_nanite_id):
    user_nanite = UserNanite.objects.get(id=user_nanite_id)
    programs = NaniteProgram.objects.all()

    if request.method == 'POST':
        program_id = request.POST.get('program_id')
        program = NaniteProgram.objects.get(id=program_id)

        UserNaniteProgram.objects.create(
            user_nanite=user_nanite,
            program=program,
            is_active=True
        )

        messages.success(request, f'Successfully added {program.name} program to your nanites.')
        return redirect('nanite_research')

    context = {
        'user_nanite': user_nanite,
        'programs': programs,
    }
    return render(request, 'nanite_program.html', context)