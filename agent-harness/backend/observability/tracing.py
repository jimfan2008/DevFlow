from opentelemetry import trace


def get_tracer(name: str = "agent-harness") -> trace.Tracer:
    return trace.get_tracer(name)
