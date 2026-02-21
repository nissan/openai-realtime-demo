"""Unit tests for observability setup - no network calls."""
import pytest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../"))


def test_setup_langfuse_tracing_with_keys():
    """Test that tracing provider is configured with OTLP exporter when keys present."""
    from observability.langfuse import setup_langfuse_tracing, shutdown_tracing

    with patch("observability.langfuse.OTLPSpanExporter") as mock_exporter_cls, \
         patch("observability.langfuse.BatchSpanProcessor") as mock_processor_cls:

        mock_exporter = MagicMock()
        mock_exporter_cls.return_value = mock_exporter
        mock_processor = MagicMock()
        mock_processor_cls.return_value = mock_processor

        provider = setup_langfuse_tracing(
            service_name="test-service",
            langfuse_host="http://localhost:3001",
            public_key="pk-test",
            secret_key="sk-test",
        )

        # Verify OTLP exporter was created with HTTP endpoint (not gRPC)
        mock_exporter_cls.assert_called_once()
        call_kwargs = mock_exporter_cls.call_args.kwargs
        assert "/api/public/otel/v1/traces" in call_kwargs["endpoint"]
        assert "http://" in call_kwargs["endpoint"]
        assert "Authorization" in call_kwargs["headers"]
        assert call_kwargs["headers"]["Authorization"].startswith("Basic ")

        shutdown_tracing()


def test_setup_langfuse_tracing_without_keys():
    """Test that console exporter is used as fallback when no keys."""
    from observability.langfuse import setup_langfuse_tracing, shutdown_tracing

    with patch("observability.langfuse.ConsoleSpanExporter") as mock_console_cls, \
         patch("observability.langfuse.BatchSpanProcessor"):

        setup_langfuse_tracing(
            service_name="test-service",
            public_key="",
            secret_key="",
        )

        mock_console_cls.assert_called_once()
        shutdown_tracing()


def test_get_tracer_returns_tracer():
    """Test that get_tracer returns a valid tracer instance."""
    from observability.langfuse import setup_langfuse_tracing, get_tracer, shutdown_tracing
    from opentelemetry import trace

    setup_langfuse_tracing("test-service", public_key="", secret_key="")
    tracer = get_tracer("test-component")

    assert tracer is not None
    assert hasattr(tracer, "start_span")
    shutdown_tracing()


def test_otel_endpoint_not_grpc():
    """Verify the OTEL endpoint is HTTP not gRPC (port 4317 would be wrong)."""
    from observability.langfuse import setup_langfuse_tracing, shutdown_tracing

    with patch("observability.langfuse.OTLPSpanExporter") as mock_exporter_cls, \
         patch("observability.langfuse.BatchSpanProcessor"):

        setup_langfuse_tracing(
            service_name="test",
            langfuse_host="http://localhost:3001",
            public_key="pk-test",
            secret_key="sk-test",
        )

        endpoint = mock_exporter_cls.call_args.kwargs["endpoint"]
        assert "4317" not in endpoint, "Must NOT use gRPC port 4317"
        assert "3001" in endpoint or "localhost" in endpoint
        shutdown_tracing()
