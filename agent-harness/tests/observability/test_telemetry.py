def test_telemetry_module_imports():
    from backend.observability.telemetry import setup_telemetry
    from backend.observability.tracing import get_tracer
    assert setup_telemetry is not None
    assert get_tracer is not None
