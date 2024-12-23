import multiprocessing
import os
import sys
import django
django.setup()
from django.utils import timezone
import tempfile
import subprocess
import logging
import psutil
import time
import threading
from main.lib.redis_client import RedisClient
from ..utils import compile_code
from ..models import Submission, SubmissionTestCase
from django.conf import settings
import socket
from main.lib.metrics import GraderMetrics
from main.lib.redis_client import RedisClient

logger = logging.getLogger(__name__)

def setup_setting_django():
    """Setup Django environment for the worker process"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'grader.settings')

class GraderManager:
    def __init__(self, num_workers=2):
        self.num_workers = num_workers
        self.redis = RedisClient.get_instance()
        self.workers = []

    def start(self):
        """Start all grader workers"""
        for i in range(self.num_workers):
            worker = GraderWorker(worker_id=i)
            process = multiprocessing.Process(target=worker.start)
            process.start()
            self.workers.append(process)

        # Wait for all workers
        for worker in self.workers:
            worker.join()

    @staticmethod
    def add_submission(submission_id):
        """Add new submission to queue"""
        redis = RedisClient.get_instance()
        redis.rpush('grading_queue', submission_id)
        redis.publish('queue_state', 'not_empty')
    @staticmethod
    def add_submission_all(submission_ids):
        """Add multiple submissions to the queue in a batch using Redis pipeline"""
        if not isinstance(submission_ids, list):
            raise ValueError("submission_ids must be a list.")
        
        redis = RedisClient.get_instance()
        pipeline = redis.pipeline()
        for submission_id in submission_ids:
            pipeline.rpush('grading_queue', submission_id)
        pipeline.execute()
        redis.publish('queue_state', 'not_empty')

class GraderWorker:
    def __init__(self, worker_id):
        self.worker_id = worker_id
        self.node_id = None
        self.processing = False
        self.should_pop = True
        self.metrics = None
        self.pubsub = None
        self.redis = None
    
    def initialize(self):
        """Initialize worker components after process start"""
        
        self.redis = RedisClient.get_instance()
        self.node_id = f"{socket.gethostname()}_{self.worker_id}"
        self.metrics = GraderMetrics()
        self.pubsub = self.redis.pubsub()

    def start(self):
        """Start the grader worker"""
        
        self.initialize()
        print(f"Starting grader worker {self.node_id}")
        # Setup monitoring threads
        self._start_pubsub_thread()
        self._start_metrics_reporter()
        
        # Main processing loop
        while True:
            try:
                if self.processing:
                    time.sleep(0.1)
                    continue

                if not self.should_pop:
                    time.sleep(1)
                    continue

                self.metrics.increment('queue_requests')
                result = self.redis.blpop('grading_queue', timeout=1)
                
                if not result:
                    self.should_pop = False
                    continue

                self._process_queue_item(result)

            except Exception as e:
                print(f"Error in grader loop: {str(e)}")
                self.processing = False

    def _process_queue_item(self, result):
        """Process a single queue item"""
        _, submission_id = result
        
        lock_key = f"processing_lock_{submission_id}"
        if not self.redis.set(lock_key, self.node_id, nx=True, ex=300):
            self.redis.rpush('grading_queue', submission_id)
            return

        try:
            start_time = time.time()
            self.processing = True
            
            submission = Submission.objects.get(id=submission_id)
            self._update_submission_status(submission, 'PROCESSING')
            
            self.process_submission(submission_id)
            
            self._update_submission_status(submission, 'COMPLETED')
            
            self.metrics.increment('submissions_processed')
            self.metrics.record_processing_time(time.time() - start_time)
            
        except Exception as e:
            self.metrics.increment('failed_submissions')
            self._handle_submission_error(submission, str(e))
            print(f"Error processing submission {submission_id}: {str(e)}")
        finally:
            self.processing = False
            self.redis.delete(lock_key)

    def process_submission(self, submission_id):
        """Process a submission"""
        submission = Submission.objects.get(id=submission_id)

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                language = submission.language
                if not language:
                    self.mark_error(submission, f"Unsupported file type: {submission.file.name}")
                    return

                compile_result = compile_code(submission, language, temp_dir)
                if not compile_result['success']:
                    self.create_result(submission, None, 'CE', 0, compile_result['message'])
                    return

                self._run_test_cases(submission, temp_dir, compile_result, language)

        except Exception as e:
            print(f"Error processing submission {submission_id}: {e}")
            self.mark_error(submission, str(e))
            self.metrics.increment("failed_submissions")

    def _run_test_cases(self, submission, temp_dir, compile_result, language):
        """Run all test cases for a submission"""
        test_cases = submission.problem.test_cases.all()
        
        for test_case in test_cases:
            result = self.run_test_case(
                submission,
                test_case,
                temp_dir,
                compile_result,  # Pass compile_result, bukan filename
                language
            )
            
            self.create_result(
                submission,
                test_case,
                result['status'],
                result['time'],
                result.get('error'),
                result.get('memory_used', 0)
            )

    def run_test_case(self, submission, test_case, temp_dir, compile_result, language):
        """Run a single test case"""
        try:
            cmd = self._get_command(language, temp_dir, compile_result, submission)
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False  # Gunakan bytes untuk I/O
            )

            # Prepare input
            input_data = test_case.input_data
            if not input_data.endswith('\n'):
                input_data += '\n'
            
           
            max_memory_used = 0
            memory_monitor_thread = None

            def monitor_memory():
                nonlocal max_memory_used
                while process.poll() is None:
                    try:
                        proc = psutil.Process(process.pid)
                        current_memory = proc.memory_info().rss / (1024 * 1024)  # MB
                        max_memory_used = max(max_memory_used, current_memory)
                        
                        if current_memory > submission.problem.memory_limit:
                            process.kill()
                            break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        break
                    time.sleep(0.1)

            start_time = time.time()
            # Start memory monitoring in separate thread
            memory_monitor_thread = threading.Thread(target=monitor_memory, daemon=True)
            memory_monitor_thread.start()

            try:
                # Run dengan timeout
                stdout, stderr = process.communicate(
                    input=input_data.encode('utf-8'), 
                    timeout=submission.problem.time_limit
                )
                exec_time = time.time() - start_time

                # Check memory limit
                if max_memory_used > submission.problem.memory_limit:
                    return {
                        'status': 'MLE',
                        'error': f"Memory limit ({submission.problem.memory_limit}MB) exceeded",
                        'time': exec_time,
                        'memory_used': max_memory_used
                    }

                # Check runtime error
                if process.returncode != 0:
                    return {
                        'status': 'RTE',
                        'error': stderr.decode('utf-8'),
                        'time': exec_time,
                        'memory_used': max_memory_used
                    }

                # Check output
                stdout = stdout.decode('utf-8').strip()
                expected = test_case.expected_output.strip()

                if stdout != expected:
                    return {
                        'status': 'WA',
                        'error': f"Expected:\n{expected}\nGot:\n{stdout}",
                        'time': exec_time,
                        'memory_used': max_memory_used
                    }

                return {
                    'status': 'AC',
                    'time': exec_time,
                    'memory_used': max_memory_used
                }

            except subprocess.TimeoutExpired:
                process.kill()
                return {
                    'status': 'TLE',
                    'error': f"Time limit ({submission.problem.time_limit}s) exceeded",
                    'time': submission.problem.time_limit,
                    'memory_used': max_memory_used
                }

        except Exception as e:
            return {
                'status': 'XX',
                'error': str(e),
                'time': 0,
                'memory_used': 0
            }
        finally:
            if process.poll() is None:
                process.kill()
            if memory_monitor_thread and memory_monitor_thread.is_alive():
                memory_monitor_thread.join(timeout=1)

    def _start_process(self, cmd):
        """Start a process with given command"""
        return subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

    def _get_command(self, language, temp_dir, compile_result, submission):
        """Get command for running code"""
        submission_dir = os.path.join(temp_dir, compile_result['filename'])
        
        cmd_map = {
            'python': ['python', os.path.join(submission_dir, 'solution.py')],
            'java': [
                'java',
                '-Xmx{}m'.format(submission.problem.memory_limit),
                '-cp', submission_dir,
                compile_result.get('main_class', 'Solution')  # Use compile_result for Java
            ],
            'c': [os.path.join(submission_dir, 'solution')],
            'cpp': [os.path.join(submission_dir, 'solution')]
        }
        
        if language not in cmd_map:
            raise ValueError(f"Unsupported language: {language}")
            
        return cmd_map[language]

    def _start_pubsub_thread(self):
        """Start Redis pub/sub listener thread"""
        def pubsub_listener():
            self.pubsub.subscribe('queue_state')
            for message in self.pubsub.listen():
                if message['type'] == 'message':
                    self.should_pop = True
                    
        thread = threading.Thread(target=pubsub_listener, daemon=True)
        thread.start()
        
    def _start_metrics_reporter(self):
        """Start metrics reporter thread"""
        def report_metrics():
            while True:
                metrics = self.metrics.get_metrics()
                print(f"Worker {self.node_id} metrics: {metrics}")
                time.sleep(60)
                
        thread = threading.Thread(target=report_metrics, daemon=True)
        thread.start()

    def _update_submission_status(self, submission, status):
        """Update submission status"""
        submission.status = status
        if status == 'PROCESSING':
            submission.started_at = timezone.now()
            submission.processing_node = self.node_id
        elif status in ['COMPLETED', 'FAILED']:
            submission.completed_at = timezone.now()
        submission.save()

    def _handle_submission_error(self, submission, error_message):
        """Handle submission error"""
        submission.status = 'FAILED'
        submission.error_message = error_message
        submission.completed_at = timezone.now()
        submission.save()

    def create_result(self, submission, test_case, status, exec_time, error=None, memory_used=0):
        """Create submission test case result"""
        SubmissionTestCase.objects.create(
            submission=submission,
            test_case=test_case,
            status=status,
            execution_time=exec_time,
            error_message=error,
            memory_used=memory_used
        )

    def mark_error(self, submission, error_message):
        """Mark submission with system error"""
        submission.status = 'FAILED'
        submission.error_message = error_message
        submission.save()
        
        SubmissionTestCase.objects.create(
            submission=submission,
            test_case=None,
            status='XX', 
            execution_time=0,
            error_message=error_message,
            memory_used=0
        )

def run_grader_workers(num_workers=None):
    setup_setting_django()
    if num_workers is None:
        num_workers = getattr(settings, 'GRADER_WORKERS', 2)
    
    if sys.platform == 'win32':
        multiprocessing.set_start_method('spawn', force=True)
    
    manager = GraderManager(num_workers)
    manager.start()