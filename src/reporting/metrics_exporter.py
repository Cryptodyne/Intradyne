# Metrics exporter for Prometheus
"""Expose Intradyne trading metrics via a Prometheus HTTP endpoint.

The exporter defines a set of gauges that are updated by the
`RealTimeReporter` (or any other component) each time new metrics are
collected.

Typical usage::

    from src.reporting.metrics_exporter import init_metrics, update_metrics
    init_metrics(port=8000)  # start /metrics endpoint
    # later, whenever you have fresh values:
    update_metrics(equity, pnl, active_positions, health_score, trade_count)

Grafana can then scrape ``http://<host>:8000/metrics`` and build dashboards.
"""

from prometheus_client import start_http_server, Gauge

# Define gauges – these will appear under the ``intradyne_`` namespace.
EQUITY_GAUGE = Gauge("intradyne_equity", "Current total equity (cash + holdings)")
PNL_GAUGE = Gauge("intradyne_pnl", "Cumulative profit and loss")
POSITIONS_GAUGE = Gauge("intradyne_active_positions", "Number of open positions")
HEALTH_GAUGE = Gauge("intradyne_health_score", "System health score (0‑100)")
TRADE_COUNT_GAUGE = Gauge("intradyne_trade_count", "Total number of trades executed")


def init_metrics(port: int = 8000) -> None:
    """Start a Prometheus HTTP server on the given port.

    The server runs in a background thread and serves ``/metrics``.
    Call this once at application start‑up.
    """
    start_http_server(port)
    print(f"[+] Prometheus metrics endpoint started on :{port}")


def update_metrics(
    equity: float | None,
    pnl: float | None,
    active_positions: int | None,
    health_score: float | None,
    trade_count: int | None = None,
) -> None:
    """Push the latest values to the Prometheus gauges.

    ``None`` values are ignored (the gauge retains its previous value).
    """
    if equity is not None:
        EQUITY_GAUGE.set(equity)
    if pnl is not None:
        PNL_GAUGE.set(pnl)
    if active_positions is not None:
        POSITIONS_GAUGE.set(active_positions)
    if health_score is not None:
        HEALTH_GAUGE.set(health_score)
    if trade_count is not None:
        TRADE_COUNT_GAUGE.set(trade_count)
