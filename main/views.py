# Create your views here.

import json
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from .lib.grader import GraderManager
from .models import Problem, Submission, TestCase

def problem_list(request):
    problems = Problem.objects.all().order_by('id')
    return render(request, 'problem_list.html', {
        'problems': problems
    })

@login_required(login_url="/auth/login")
def problem_detail(request, problem_id):
    """
    View untuk detail problem yang menampilkan:
    1. Spesifikasi problem
    2. Form submission (code editor/file upload)
    3. Riwayat submission dengan detail test cases
    """
    problem = get_object_or_404(Problem, id=problem_id)
    
    # Ambil semua submission untuk problem ini dari user yang login
    submissions = Submission.objects.filter(
        problem=problem,
        user=request.user
    ).order_by('-submitted_at').prefetch_related('test_results')
    
    return render(request, 'problem_detail.html', {
        'problem': problem,
        'submissions': submissions
    })

@login_required(login_url="/auth/login")
@require_http_methods(["POST"])
def submit_solution(request, problem_id):
    """AJAX endpoint untuk handle submission code"""
    try:
        problem = get_object_or_404(Problem, id=problem_id)
        
        # Handle code dari form atau file
        if 'file' in request.FILES:
            file = request.FILES['file']
            code = file.read().decode('utf-8')
            
            # Get language from file extension
            extension = file.name.split('.')[-1].lower()
            extension_to_language = {
                'py': 'python',
                'java': 'java',
                'cpp': 'cpp',
                'c': 'c'
            }
            language = extension_to_language.get(extension)
            
            if not language:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Unsupported file type: .{extension}'
                }, status=400)
        else:
            code = request.POST.get('code')
            language = request.POST.get('language')
            
            if not language:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Language must be specified when using code editor'
                }, status=400)
            
        if not code:
            return JsonResponse({
                'status': 'error',
                'message': 'No code provided'
            }, status=400)

        # Validate language
        if language not in dict(Submission.LANGUAGE_CHOICES):
            return JsonResponse({
                'status': 'error',
                'message': f'Unsupported language: {language}'
            }, status=400)

        # Buat submission baru
        submission = Submission.objects.create(
            user=request.user,
            problem=problem,
            code=code,
            language=language,
            status='QUEUED',
            submitted_at=timezone.now()
        )

        # Masukkan ke queue untuk diproses
        GraderManager.add_submission(submission.id)

        return JsonResponse({
            'status': 'success',
            'submission_id': submission.id
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)
    
@login_required(login_url="/auth/login")
def get_submission_status(request, submission_id):
    """AJAX endpoint untuk get status dan hasil test case submission"""
    try:
        submission = get_object_or_404(
            Submission, 
            id=submission_id,
            user=request.user
        )
        
        response = {
            'id': submission.id,
            'status': submission.status,
            'submitted_at': submission.submitted_at,
            'test_results': []
        }

        if submission.status in ['COMPLETED', 'FAILED']:
            for result in submission.test_results.all():
                response['test_results'].append({
                    'status': result.status,  # AC, WA, TLE, etc
                    'execution_time': result.execution_time,
                    'memory_used': result.memory_used,
                    'error_message': result.error_message
                })

        return JsonResponse(response)

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required(login_url="/auth/login")   
def problem_create(request):
    """View untuk membuat problem baru"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            problem = Problem.objects.create(
                title=data['title'],
                description=data['description'],
                memory_limit=int(data.get('memory_limit', 256)),
                time_limit=float(data.get('time_limit', 1.0)),
                created_by= request.user
            )
            
            # Create test cases
            for test_case in data.get('test_cases', []):
                TestCase.objects.create(
                    problem=problem,
                    input_data=test_case['input'],
                    expected_output=test_case['output']
                )
            
            return JsonResponse({
                'status': 'success',
                'problem_id': problem.id,
                'message': 'Problem created successfully'
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
            
    return render(request, 'problem_form.html', {
        'mode': 'create'
    })

@login_required(login_url="/auth/login") 
def problem_update(request, problem_id):
    problem = get_object_or_404(Problem, id=problem_id, created_by=request.user)
    submissions = Submission.objects.filter(problem= problem)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            problem.title = data.get('title', problem.title)
            problem.description = data.get('description', problem.description)
            problem.memory_limit = int(data.get('memory_limit', problem.memory_limit))
            problem.time_limit = float(data.get('time_limit', problem.time_limit))
            problem.save()
            
            if 'test_cases' in data:
                # Replace all test cases
                problem.test_cases.all().delete()
                for test_case in data['test_cases']:
                    TestCase.objects.create(
                        problem=problem,
                        input_data=test_case['input'],
                        expected_output=test_case['output']
                    )
            submission_ids = [submission.id for submission in submissions]
            GraderManager.add_submission_all(submission_ids)
            
            return JsonResponse({
                'status': 'success',
                'message': 'Problem updated successfully'
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
    
    return render(request, 'problem_form.html', {
        'mode': 'update',
        'problem': problem
    })

@login_required(login_url="/auth/login")
def my_problems(request):
    """View untuk menampilkan problem yang dibuat oleh user"""
    problems = Problem.objects.filter(created_by=request.user).order_by('-created_at')
    return render(request, 'my_problems.html', {
        'problems': problems
    })