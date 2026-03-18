"""Shared in-memory state for healthcare RX capture and verification."""

from __future__ import annotations

import threading
from typing import Any


def _normalize_name(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


class HealthcareVerificationSession:
    """Track RX candidates and verification progress from live detections."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self.mode = "idle"
            self.rx_candidates: list[str] = []
            self.rx_list: list[str] = []
            self.detected: dict[str, bool] = {}
            self.last_labels: list[str] = []
            self.complete = False

    def _sync_complete_locked(self) -> None:
        self.complete = bool(self.detected) and all(self.detected.values())

    def _matrix_rows_locked(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for medicine in self.rx_list:
            is_detected = bool(self.detected.get(medicine, False))
            rows.append(
                {
                    "medicine": medicine,
                    "in_rx": True,
                    "detected": is_detected,
                    "status": "MATCH" if is_detected else "MISSING",
                }
            )
        return rows

    def start_capture(self, reset: bool = True) -> dict[str, Any]:
        with self._lock:
            self.mode = "capture"
            self.rx_candidates = []
            if reset:
                self.rx_list = []
                self.detected = {}
            self.complete = False
            return self._snapshot_locked()

    def confirm_rx_list(self, medicines: list[str]) -> dict[str, Any]:
        cleaned = [item.strip() for item in medicines if item and item.strip()]
        with self._lock:
            if not cleaned:
                cleaned = list(self.rx_candidates)

            self.rx_list = cleaned
            self.detected = {name: False for name in self.rx_list}
            self.complete = False
            self.mode = "ready"
            return self._snapshot_locked()

    def add_captured_items(self, medicines: list[str]) -> dict[str, Any]:
        cleaned = [item.strip() for item in medicines if item and item.strip()]
        with self._lock:
            source = cleaned if cleaned else list(self.rx_candidates)
            for item in source:
                if item not in self.rx_list:
                    self.rx_list.append(item)
                if item not in self.detected:
                    self.detected[item] = False

            self.mode = "capture"
            self._sync_complete_locked()
            return self._snapshot_locked()

    def finish_capture(self) -> dict[str, Any]:
        with self._lock:
            if not self.rx_list:
                for item in self.rx_candidates:
                    if item not in self.rx_list:
                        self.rx_list.append(item)
                    if item not in self.detected:
                        self.detected[item] = False

            self.mode = "ready"
            self._sync_complete_locked()
            return self._snapshot_locked()

    def start_verification(self) -> dict[str, Any]:
        with self._lock:
            if not self.rx_list:
                self.rx_list = list(self.rx_candidates)
            self.detected = {name: False for name in self.rx_list}
            self.mode = "verify"
            self.complete = False
            return self._snapshot_locked()

    def stop_verification(self) -> dict[str, Any]:
        with self._lock:
            if self.mode == "capture" and self.rx_list:
                self.mode = "ready"
            else:
                self.mode = "idle"
            return self._snapshot_locked()

    def update_from_detections(self, detections: list[dict[str, Any]]) -> None:
        labels = [str(item.get("class", "")).strip() for item in detections]
        labels = [label for label in labels if label]
        with self._lock:
            self.last_labels = labels

            if self.mode == "capture":
                # Capture a short list of unique labels while looking at the RX source.
                for label in labels:
                    if label not in self.rx_candidates:
                        self.rx_candidates.append(label)
                    if len(self.rx_candidates) >= 8:
                        break
                return

            if self.mode != "verify":
                return

            normalized_labels = [_normalize_name(label) for label in labels]
            for medicine in list(self.detected):
                med_norm = _normalize_name(medicine)
                if not med_norm:
                    continue
                if any(med_norm in lbl or lbl in med_norm for lbl in normalized_labels if lbl):
                    self.detected[medicine] = True

            self._sync_complete_locked()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return self._snapshot_locked()

    def _snapshot_locked(self) -> dict[str, Any]:
        total = len(self.rx_list)
        matched = sum(1 for value in self.detected.values() if value)
        return {
            "mode": self.mode,
            "rx_candidates": list(self.rx_candidates),
            "rx_list": list(self.rx_list),
            "matrix": self._matrix_rows_locked(),
            "matched": matched,
            "total": total,
            "complete": self.complete,
            "last_labels": list(self.last_labels),
        }


_session = HealthcareVerificationSession()


def get_healthcare_session() -> HealthcareVerificationSession:
    return _session
