from django.urls import path
from . import views

app_name = 'main'

urlpatterns = [
    # Problem views
    path('problems/', views.problem_list, name='problem_list'),
    path('problems/my/', views.my_problems, name='my_problems'),
    path('problems/create/', views.problem_create, name='problem_create'),
    path('problems/<int:problem_id>/', views.problem_detail, name='problem_detail'),
    path('problems/<int:problem_id>/edit/', views.problem_update, name='problem_update'),
    
    # Submission endpoints
    path('problems/<int:problem_id>/submit/', views.submit_solution, name='submit_solution'),
    path('submissions/<int:submission_id>/status/', views.get_submission_status, name='submission_status'),
]