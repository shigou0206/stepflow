
"""OpenTelemetry tracer initialization."""

import os
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

from stepflow.config import ENABLE_OTEL, OTEL_EXPORTER_ENDPOINT


def init_tracer(service_name: str = "stepflow") -> None:
    """Set up OpenTelemetry tracing if ENABLE_OTEL is true."""
    if not ENABLE_OTEL:
        return

    resource = Resource.create({"service.name": service_name})

    provider = TracerProvider(resource=resource)
    span_processor = BatchSpanProcessor(
        OTLPSpanExporter(endpoint=OTEL_EXPORTER_ENDPOINT)
    )
    provider.add_span_processor(span_processor)

    trace.set_tracer_provider(provider)
