from django.contrib import admin
from .models import Problem, TestCase, Submission, SubmissionTestCase
# Register your models here.
admin.register(Problem)
admin.register(TestCase)
admin.register(Submission)
admin.register(SubmissionTestCase)
#