"""
OTEL + Langfuse observability setup.
CRITICAL: Use HTTP/protobuf endpoint /api/public/otel/v1/traces NOT gRPC.
"""
import os
from typing import Optional
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
import logging

logger = logging.getLogger(__name__)

_tracer_provider: Optional[TracerProvider] = None


def setup_langfuse_tracing(
    service_name: str,
    langfuse_host: Optional[str] = None,
    public_key: Optional[str] = None,
    secret_key: Optional[str] = None,
) -> TracerProvider:
    """
    Configure OTEL tracing to export to Langfuse via HTTP/protobuf.

    CRITICAL: endpoint must be /api/public/otel/v1/traces (NOT gRPC port 4317).
    Auth header format: Basic base64(public_key:secret_key)
    """
    global _tracer_provider

    host = langfuse_host or os.environ.get("LANGFUSE_HOST", "http://localhost:3001")
    pk = public_key or os.environ.get("LANGFUSE_PUBLIC_KEY", "")
    sk = secret_key or os.environ.get("LANGFUSE_SECRET_KEY", "")

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    # HTTP/protobuf exporter to Langfuse OTEL endpoint
    if pk and sk:
        import base64
        auth = base64.b64encode(f"{pk}:{sk}".encode()).decode()
        endpoint = f"{host.rstrip('/')}/api/public/otel/v1/traces"

        exporter = OTLPSpanExporter(
            endpoint=endpoint,
            headers={"Authorization": f"Basic {auth}"},
        )
        provider.add_span_processor(BatchSpanProcessor(exporter))
        logger.info(f"Langfuse OTEL tracing configured: {endpoint}")
    else:
        # Fallback: console exporter for local dev without keys
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        logger.warning("No Langfuse keys found, using console span exporter")

    trace.set_tracer_provider(provider)
    _tracer_provider = provider
    return provider


def get_tracer(name: str) -> trace.Tracer:
    """Get a tracer. Call setup_langfuse_tracing() first."""
    return trace.get_tracer(name)


def shutdown_tracing() -> None:
    """Flush and shutdown the tracer provider."""
    global _tracer_provider
    if _tracer_provider:
        _tracer_provider.shutdown()
        _tracer_provider = None
