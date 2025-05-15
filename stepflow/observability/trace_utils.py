
"""Utility for creating spans easily."""

import os
import contextlib
from opentelemetry import trace
from stepflow.config import ENABLE_OTEL

@contextlib.asynccontextmanager
async def traced_span(name: str, **attrs):
    """Async context manager that generates a span if tracing is enabled."""
    if not ENABLE_OTEL:
        yield
        return

    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span(name) as span:
        for k, v in attrs.items():
            span.set_attribute(k, v)
        yield
