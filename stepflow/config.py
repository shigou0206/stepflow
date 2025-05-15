
import os

# Feature toggles
ENABLE_PROMETHEUS: bool = os.getenv("ENABLE_PROMETHEUS", "true").lower() == "true"
ENABLE_OTEL: bool = os.getenv("ENABLE_OTEL", "true").lower() == "true"

# OpenTelemetry exporter endpoint
OTEL_EXPORTER_ENDPOINT: str = os.getenv(
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "http://localhost:4318/v1/traces",
)
