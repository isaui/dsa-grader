# Generated by Django 4.2.16 on 2024-12-23 10:41

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Problem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('memory_limit', models.IntegerField(default=256)),
                ('time_limit', models.FloatField(default=1.0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Submission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.TextField()),
                ('language', models.CharField(choices=[('python', 'Python'), ('java', 'Java'), ('cpp', 'C++'), ('c', 'C')], max_length=10)),
                ('submitted_at', models.DateTimeField(auto_now_add=True)),
                ('status', models.CharField(choices=[('QUEUED', 'In Queue'), ('PROCESSING', 'Processing'), ('COMPLETED', 'Completed'), ('FAILED', 'Failed')], default='QUEUED', max_length=20)),
                ('error_message', models.TextField(blank=True, null=True)),
                ('started_at', models.DateTimeField(null=True)),
                ('completed_at', models.DateTimeField(null=True)),
                ('processing_node', models.CharField(max_length=100, null=True)),
                ('problem', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='main.problem')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='TestCase',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('input_data', models.TextField()),
                ('expected_output', models.TextField()),
                ('problem', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='test_cases', to='main.problem')),
            ],
        ),
        migrations.CreateModel(
            name='SubmissionTestCase',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('AC', 'Accepted'), ('WA', 'Wrong Answer'), ('RTE', 'Runtime Error'), ('TLE', 'Time Limit Exceeded'), ('SG', 'Program Died on a Signal'), ('MLE', 'Memory Limit Exceeded'), ('XX', 'Unknown Error')], max_length=3)),
                ('execution_time', models.FloatField()),
                ('error_message', models.TextField(blank=True, null=True)),
                ('memory_used', models.FloatField()),
                ('submission', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='test_results', to='main.submission')),
                ('test_case', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='main.testcase')),
            ],
        ),
    ]
