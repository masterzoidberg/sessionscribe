"""
Prometheus metrics for SessionScribe services.
Tracks performance and operational metrics without exposing PHI.
"""

import os
from typing import Dict, Optional
from prometheus_client import Counter, Gauge, Histogram, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
import time

class SessionScribeMetrics:
    """Base metrics collector for SessionScribe services."""
    
    def __init__(self, service_name: str, service_port: int):
        self.service_name = service_name
        self.service_port = service_port
        self.registry = CollectorRegistry()
        self.enabled = os.getenv('OBSERVABILITY_ENABLED', 'true').lower() == 'true'
        
        if not self.enabled:
            return
        
        # Common metrics across all services
        self.request_duration = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration in seconds',
            labelnames=['method', 'endpoint', 'status'],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0],
            registry=self.registry
        )
        
        self.request_count = Counter(
            'http_requests_total',
            'Total HTTP requests',
            labelnames=['method', 'endpoint', 'status'],
            registry=self.registry
        )
        
        self.active_sessions = Gauge(
            'active_sessions',
            'Number of active sessions',
            registry=self.registry
        )
        
        self.service_uptime = Gauge(
            'service_uptime_seconds',
            'Service uptime in seconds',
            registry=self.registry
        )
        
        self.start_time = time.time()
    
    def record_request(self, method: str, endpoint: str, status: int, duration: float):
        """Record HTTP request metrics."""
        if not self.enabled:
            return
        
        # Sanitize endpoint - remove session IDs and other dynamic parts
        sanitized_endpoint = self._sanitize_endpoint(endpoint)
        
        self.request_duration.labels(
            method=method,
            endpoint=sanitized_endpoint,
            status=str(status)
        ).observe(duration)
        
        self.request_count.labels(
            method=method,
            endpoint=sanitized_endpoint,
            status=str(status)
        ).inc()
    
    def update_active_sessions(self, count: int):
        """Update active sessions gauge."""
        if self.enabled:
            self.active_sessions.set(count)
    
    def update_uptime(self):
        """Update service uptime."""
        if self.enabled:
            uptime = time.time() - self.start_time
            self.service_uptime.set(uptime)
    
    def _sanitize_endpoint(self, endpoint: str) -> str:
        """Sanitize endpoint path to remove dynamic segments."""
        # Replace UUIDs and session IDs with placeholder
        import re
        # UUID pattern
        endpoint = re.sub(r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '/:id', endpoint)
        # Numeric IDs
        endpoint = re.sub(r'/\d+', '/:id', endpoint)
        return endpoint
    
    def generate_metrics(self) -> str:
        """Generate Prometheus metrics output."""
        if not self.enabled:
            return "# HELP observability_disabled Observability disabled\n# TYPE observability_disabled gauge\nobservability_disabled 1\n"
        
        self.update_uptime()
        return generate_latest(self.registry).decode('utf-8')

class ASRMetrics(SessionScribeMetrics):
    """ASR service specific metrics."""
    
    def __init__(self):
        super().__init__("asr", 7035)
        
        if not self.enabled:
            return
        
        # ASR specific metrics
        self.transcription_latency = Histogram(
            'asr_transcription_latency_seconds',
            'ASR transcription end-to-end latency',
            buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0],
            registry=self.registry
        )
        
        self.audio_input_buffer_depth = Gauge(
            'asr_audio_input_buffer_depth',
            'Current audio frames in input buffer',
            registry=self.registry
        )
        
        self.frames_dropped_total = Counter(
            'asr_frames_dropped_total',
            'Total audio frames dropped',
            labelnames=['reason'],
            registry=self.registry
        )
        
        self.chunks_processed_total = Counter(
            'asr_chunks_processed_total',
            'Total audio chunks processed',
            labelnames=['channel', 'format'],
            registry=self.registry
        )
        
        self.websocket_connections = Gauge(
            'asr_websocket_connections_active',
            'Active WebSocket connections',
            registry=self.registry
        )
    
    def record_transcription_latency(self, duration: float):
        """Record transcription processing time."""
        if self.enabled:
            self.transcription_latency.observe(duration)
    
    def update_buffer_depth(self, frames: int):
        """Update audio buffer depth."""
        if self.enabled:
            self.audio_input_buffer_depth.set(frames)
    
    def record_dropped_frames(self, count: int, reason: str):
        """Record dropped frames."""
        if self.enabled:
            self.frames_dropped_total.labels(reason=reason).inc(count)
    
    def record_chunk_processed(self, channel: str, audio_format: str):
        """Record processed audio chunk."""
        if self.enabled:
            self.chunks_processed_total.labels(channel=channel, format=audio_format).inc()
    
    def update_websocket_connections(self, count: int):
        """Update WebSocket connection count."""
        if self.enabled:
            self.websocket_connections.set(count)

class RedactionMetrics(SessionScribeMetrics):
    """Redaction service specific metrics."""
    
    def __init__(self):
        super().__init__("redaction", 7032)
        
        if not self.enabled:
            return
        
        self.phi_entities_detected_total = Counter(
            'redaction_phi_entities_detected_total',
            'Total PHI entities detected',
            labelnames=['entity_type', 'detection_method'],
            registry=self.registry
        )
        
        self.redaction_processing_duration = Histogram(
            'redaction_processing_duration_seconds',
            'Time to process redaction request',
            buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0],
            registry=self.registry
        )
        
        self.text_chunks_processed_total = Counter(
            'redaction_text_chunks_processed_total',
            'Total text chunks processed',
            registry=self.registry
        )
    
    def record_phi_entity(self, entity_type: str, method: str):
        """Record PHI entity detection (metadata only)."""
        if self.enabled:
            self.phi_entities_detected_total.labels(
                entity_type=entity_type,
                detection_method=method
            ).inc()
    
    def record_processing_duration(self, duration: float):
        """Record redaction processing time."""
        if self.enabled:
            self.redaction_processing_duration.observe(duration)
    
    def record_chunk_processed(self):
        """Record text chunk processed."""
        if self.enabled:
            self.text_chunks_processed_total.inc()

class InsightsMetrics(SessionScribeMetrics):
    """Insights Bridge service specific metrics."""
    
    def __init__(self):
        super().__init__("insights", 7033)
        
        if not self.enabled:
            return
        
        self.llm_request_duration = Histogram(
            'insights_llm_request_duration_seconds',
            'LLM API request duration',
            labelnames=['provider', 'model'],
            buckets=[1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0],
            registry=self.registry
        )
        
        self.llm_requests_total = Counter(
            'insights_llm_requests_total',
            'Total LLM API requests',
            labelnames=['provider', 'model', 'status'],
            registry=self.registry
        )
        
        self.token_usage_total = Counter(
            'insights_token_usage_total',
            'Total tokens used',
            labelnames=['provider', 'model', 'type'],
            registry=self.registry
        )
    
    def record_llm_request(self, provider: str, model: str, duration: float, status: str, 
                          prompt_tokens: int = 0, completion_tokens: int = 0):
        """Record LLM API request metrics."""
        if not self.enabled:
            return
        
        self.llm_request_duration.labels(provider=provider, model=model).observe(duration)
        self.llm_requests_total.labels(provider=provider, model=model, status=status).inc()
        
        if prompt_tokens > 0:
            self.token_usage_total.labels(provider=provider, model=model, type="prompt").inc(prompt_tokens)
        if completion_tokens > 0:
            self.token_usage_total.labels(provider=provider, model=model, type="completion").inc(completion_tokens)

class NoteBuilderMetrics(SessionScribeMetrics):
    """Note Builder service specific metrics."""
    
    def __init__(self):
        super().__init__("note_builder", 7034)
        
        if not self.enabled:
            return
        
        self.notes_generated_total = Counter(
            'notes_notes_generated_total',
            'Total notes generated',
            labelnames=['format', 'template'],
            registry=self.registry
        )
        
        self.note_generation_duration = Histogram(
            'notes_generation_duration_seconds',
            'Time to generate note',
            buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0],
            registry=self.registry
        )
    
    def record_note_generated(self, format_type: str, template: str, duration: float):
        """Record note generation metrics."""
        if not self.enabled:
            return
        
        self.notes_generated_total.labels(format=format_type, template=template).inc()
        self.note_generation_duration.observe(duration)

# Global metrics instances - lazy initialized
_asr_metrics: Optional[ASRMetrics] = None
_redaction_metrics: Optional[RedactionMetrics] = None
_insights_metrics: Optional[InsightsMetrics] = None  
_note_builder_metrics: Optional[NoteBuilderMetrics] = None

def get_asr_metrics() -> ASRMetrics:
    """Get ASR metrics instance."""
    global _asr_metrics
    if _asr_metrics is None:
        _asr_metrics = ASRMetrics()
    return _asr_metrics

def get_redaction_metrics() -> RedactionMetrics:
    """Get redaction metrics instance."""
    global _redaction_metrics
    if _redaction_metrics is None:
        _redaction_metrics = RedactionMetrics()
    return _redaction_metrics

def get_insights_metrics() -> InsightsMetrics:
    """Get insights metrics instance."""
    global _insights_metrics
    if _insights_metrics is None:
        _insights_metrics = InsightsMetrics()
    return _insights_metrics

def get_note_builder_metrics() -> NoteBuilderMetrics:
    """Get note builder metrics instance."""
    global _note_builder_metrics
    if _note_builder_metrics is None:
        _note_builder_metrics = NoteBuilderMetrics()
    return _note_builder_metrics