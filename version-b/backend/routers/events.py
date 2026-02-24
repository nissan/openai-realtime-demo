"""Frontend event ingestion — proxies browser events to Langfuse via OTEL."""
from fastapi import APIRouter, BackgroundTasks
from opentelemetry import trace
from pydantic import BaseModel

router = APIRouter(tags=["events"])
tracer = trace.get_tracer("frontend-events")


class FrontendEvent(BaseModel):
    session_id: str
    event_name: str
    attributes: dict[str, str | int | float | bool] = {}


@router.post("/events")
async def ingest_frontend_event(event: FrontendEvent, background_tasks: BackgroundTasks) -> dict:
    """Receive frontend telemetry events and forward to Langfuse via OTEL."""
    background_tasks.add_task(_record_span, event)
    return {"ok": True}


def _record_span(event: FrontendEvent) -> None:
    with tracer.start_as_current_span(f"frontend.{event.event_name}") as span:
        span.set_attribute("session.id", event.session_id)
        span.set_attribute("source", "frontend")
        for k, v in event.attributes.items():
            span.set_attribute(f"frontend.{k}", v)
