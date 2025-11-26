# Real-time reporting for continuous trading
"""Utility to generate periodic reports of the trading system.

The `RealTimeReporter` runs in a separate thread/process and writes
key metrics (equity, P&L, active positions, health score) to a CSV
file every `report_interval` seconds. The Streamlit UI can read this
file to display a live report.
"""

import csv
import os
import time
from datetime import datetime
from threading import Event, Thread

class RealTimeReporter:
    def __init__(self, trader, output_path="reports/real_time_report.csv", report_interval: int = 60):
        self.trader = trader
        self.output_path = output_path
        self.report_interval = report_interval
        self._stop_event = Event()
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        # Write header if file does not exist
        if not os.path.isfile(self.output_path):
            with open(self.output_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "equity", "pnl", "active_positions", "health_score"])

    def _collect_metrics(self):
        # Pull metrics from the trader (assumes trader exposes these attributes)
        equity = getattr(self.trader, "equity", None)
        pnl = getattr(self.trader, "pnl", None)
        active_positions = getattr(self.trader, "active_positions", None)
        health_score = getattr(self.trader, "health_score", None)
        return equity, pnl, active_positions, health_score

    def _write_report(self):
        equity, pnl, active_positions, health_score = self._collect_metrics()
        timestamp = datetime.utcnow().isoformat()
        with open(self.output_path, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, equity, pnl, active_positions, health_score])

    def _run(self):
        while not self._stop_event.is_set():
            self._write_report()
            self._stop_event.wait(self.report_interval)

    def start(self):
        self.thread = Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self._stop_event.set()
        self.thread.join()
