import logging
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from prometheus_client import make_asgi_app
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics import MeterProvider

def setup_telemetry(app=None, is_worker=False):
    """
    Initializes OpenTelemetry distributed tracing and Prometheus metrics.
    Preserves existing architecture while propagating context across FastAPI -> Celery.
    """
    service_name = "documind-worker" if is_worker else "documind-api"
    resource = Resource.create({SERVICE_NAME: service_name})
    
    # 1. Setup Distributed Tracing
    tracer_provider = TracerProvider(resource=resource)
    # Using Console exporter for observability in docker logs. 
    # In production, replace with OTLPSpanExporter for Jaeger/Tempo/Datadog.
    tracer_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(tracer_provider)
    
    # 2. Setup Metrics (Prometheus Exporter)
    metric_reader = PrometheusMetricReader()
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    # 3. Apply Instrumentation
    if app and not is_worker:
        # Auto-instruments HTTP routes, injecting/extracting TraceContext
        FastAPIInstrumentor.instrument_app(app)
        
        # Mount Prometheus metrics endpoint
        metrics_app = make_asgi_app()
        app.mount("/metrics", metrics_app)
        
    if is_worker:
        # Auto-instruments Celery tasks, continuing TraceContext from the API message broker
        CeleryInstrumentor().instrument()

    logging.info(f"[Telemetry] OpenTelemetry initialized for {service_name}")
