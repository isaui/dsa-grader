class GraderMetrics:
    def __init__(self):
        self._metrics = {
            'queue_requests': 0,
            'submissions_processed': 0,
            'failed_submissions': 0,
            'total_processing_time': 0
        }
        
    def increment(self, metric):
        self._metrics[metric] = self._metrics.get(metric, 0) + 1
        
    def get_metrics(self):
        return self._metrics.copy()
        
    def record_processing_time(self, time_taken):
        self._metrics['total_processing_time'] += time_taken