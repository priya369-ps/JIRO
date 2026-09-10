"""Content-free performance measurements for the tailoring workflow."""

from dataclasses import dataclass
from time import perf_counter
import tracemalloc


@dataclass(frozen=True)
class PerformanceMetrics:
    """Timing and peak-memory measurements safe to return with a result."""

    input_parsing_ms: float = 0.0
    analysis_ms: float = 0.0
    matching_ms: float = 0.0
    provider_ms: float = 0.0
    validation_ms: float = 0.0
    export_ms: float = 0.0
    total_ms: float = 0.0
    peak_memory_bytes: int = 0


class PerformanceMonitor:
    """Measure named workflow stages without retaining the measured inputs."""

    def __init__(self) -> None:
        self._durations: dict[str, float] = {}
        self._started = perf_counter()
        self._tracing_started = tracemalloc.is_tracing()
        if not self._tracing_started:
            tracemalloc.start()

    def measure(self, stage: str):
        """Return a context manager that records a stage duration in milliseconds."""
        return _StageTimer(self, stage)

    def report(self) -> PerformanceMetrics:
        """Return a stable report and restore the caller's tracing state."""
        _, peak = tracemalloc.get_traced_memory()
        if not self._tracing_started:
            tracemalloc.stop()
        return PerformanceMetrics(
            **self._durations,
            total_ms=(perf_counter() - self._started) * 1000,
            peak_memory_bytes=peak,
        )

    def _record(self, stage: str, started: float) -> None:
        self._durations[f"{stage}_ms"] = (perf_counter() - started) * 1000


class _StageTimer:
    def __init__(self, monitor: PerformanceMonitor, stage: str) -> None:
        self._monitor = monitor
        self._stage = stage
        self._started = 0.0

    def __enter__(self) -> "_StageTimer":
        self._started = perf_counter()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self._monitor._record(self._stage, self._started)