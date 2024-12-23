from django.db import models
from django.contrib.auth.models import User

class Problem(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    memory_limit = models.IntegerField(default=256)  # dalam MB
    time_limit = models.FloatField(default=1.0)  # dalam detik
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    def __str__(self):
        return self.title

class TestCase(models.Model):
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE,related_name='test_cases')
    input_data = models.TextField()
    expected_output = models.TextField()
    
    def __str__(self):
        return f"TC {self.id} - {self.problem.title}"

class Submission(models.Model):
    STATUS_CHOICES = [
        ('QUEUED', 'In Queue'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed')
    ]
    
    LANGUAGE_CHOICES = [
        ('python', 'Python'),
        ('java', 'Java'),
        ('cpp', 'C++'),
        ('c', 'C')
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    code = models.TextField()
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES)
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='QUEUED')
    error_message = models.TextField(null=True, blank=True)
    started_at = models.DateTimeField(null=True)
    completed_at = models.DateTimeField(null=True)
    processing_node = models.CharField(max_length=100, null=True)
class SubmissionTestCase(models.Model):
    STATUS_CHOICES = [
        ('AC', 'Accepted'),
        ('WA', 'Wrong Answer'),
        ('RTE', 'Runtime Error'),
        ('TLE', 'Time Limit Exceeded'),
        ('SG', 'Program Died on a Signal'),
        ('MLE', 'Memory Limit Exceeded'),
        ('XX', 'Unknown Error')
    ]

    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='test_results')
    test_case = models.ForeignKey(TestCase, on_delete=models.CASCADE)
    status = models.CharField(max_length=3, choices=STATUS_CHOICES)
    execution_time = models.FloatField()  # dalam detik
    error_message = models.TextField(null=True, blank=True)
    memory_used = models.FloatField()
    
    def __str__(self):
        return f"TC {self.test_case.id} result for submission {self.submission.id}"