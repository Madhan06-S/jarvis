"""
JARVIS CYBER DEFENSE SYSTEM
Real-time network monitoring, anomaly detection, threat intelligence.
Uses psutil for network stats, monitors connections, detects suspicious patterns.
"""
import time
import asyncio
import socket
import json
import os
from typing import Optional
from collections import defaultdict, deque

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

THREAT_DB_FILE = os.path.join(os.path.dirname(__file__), "data", "threat_db.json")

# Known suspicious ports
SUSPICIOUS_PORTS = {
    4444, 1337, 31337, 6666, 6667, 6668, 6669,  # common RAT/backdoor ports
    23, 2323,  # Telnet
    5900, 5901,  # VNC
    3389,  # RDP (flag if unexpected)
    8080, 8443,  # common proxy/C2 ports
}

# Known malicious IP ranges (simplified)
SUSPICIOUS_IP_PREFIXES = [
    "185.220.",  # Tor exit nodes
    "198.96.",   # known scanning ranges
]


class CyberDefenseSystem:
    def __init__(self):
        self.is_running       = False
        self.threat_level     = 0       # 0-10
        self.active_threats   = []
        self.blocked_ips      = set()
        self.connection_log   = deque(maxlen=100)
        self.anomaly_log      = deque(maxlen=50)
        self.scan_count       = 0
        self._baseline_conns  = None
        self._conn_history    = deque(maxlen=30)
        self._task: Optional[asyncio.Task] = None
        self._callbacks       = []

        self._load_threat_db()

    def is_available(self) -> bool:
        return PSUTIL_AVAILABLE

    def start(self):
        if not self.is_available():
            print("[CyberDefense] psutil not available.")
            return False
        if self.is_running:
            return True
        self.is_running = True
        self._task = asyncio.create_task(self._monitor_loop())
        print("[CyberDefense] Cyber defense system online.")
        return True

    def stop(self):
        self.is_running = False

    def on_threat(self, callback):
        self._callbacks.append(callback)

    def get_status(self) -> dict:
        return {
            "available":     self.is_available(),
            "running":       self.is_running,
            "threat_level":  self.threat_level,
            "active_threats": self.active_threats[-5:],
            "blocked_ips":   list(self.blocked_ips)[:10],
            "scan_count":    self.scan_count,
            "recent_anomalies": list(self.anomaly_log)[-5:],
            "connection_count": len(self.connection_log),
        }

    def get_network_stats(self) -> dict:
        if not PSUTIL_AVAILABLE:
            return {}
        try:
            net = psutil.net_io_counters()
            conns = psutil.net_connections(kind="inet")
            return {
                "bytes_sent":    net.bytes_sent,
                "bytes_recv":    net.bytes_recv,
                "packets_sent":  net.packets_sent,
                "packets_recv":  net.packets_recv,
                "active_conns":  len([c for c in conns if c.status == "ESTABLISHED"]),
                "listening":     len([c for c in conns if c.status == "LISTEN"]),
                "total_conns":   len(conns),
            }
        except Exception:
            return {}

    # ── Monitor Loop ──────────────────────────────────────────────────────────

    async def _monitor_loop(self):
        loop = asyncio.get_event_loop()
        while self.is_running:
            try:
                threats = await loop.run_in_executor(None, self._scan)
                if threats:
                    for t in threats:
                        self._fire_threat(t)
            except Exception as e:
                print(f"[CyberDefense] Scan error: {e}")
            await asyncio.sleep(5.0)

    def _scan(self) -> list:
        self.scan_count += 1
        threats = []

        try:
            conns = psutil.net_connections(kind="inet")
        except Exception:
            return []

        self._conn_history.append(len(conns))

        # Establish baseline on first scan
        if self._baseline_conns is None:
            self._baseline_conns = len(conns)

        # Check for connection spike
        if len(self._conn_history) >= 5:
            avg = sum(list(self._conn_history)[:-1]) / (len(self._conn_history) - 1)
            current = self._conn_history[-1]
            if current > avg * 2.5 and current > avg + 20:
                threat = {
                    "type":     "connection_spike",
                    "severity": "medium",
                    "detail":   f"Connection count spiked: {current} vs avg {avg:.0f}",
                    "time":     time.time(),
                }
                threats.append(threat)
                self.anomaly_log.append(threat)

        # Check each connection
        for conn in conns:
            if not conn.raddr:
                continue

            remote_ip   = conn.raddr.ip
            remote_port = conn.raddr.port

            # Suspicious port check
            if remote_port in SUSPICIOUS_PORTS:
                threat = {
                    "type":     "suspicious_port",
                    "severity": "high",
                    "detail":   f"Connection to suspicious port {remote_port} at {remote_ip}",
                    "ip":       remote_ip,
                    "port":     remote_port,
                    "time":     time.time(),
                }
                threats.append(threat)
                self.anomaly_log.append(threat)

            # Suspicious IP check
            for prefix in SUSPICIOUS_IP_PREFIXES:
                if remote_ip.startswith(prefix):
                    threat = {
                        "type":     "suspicious_ip",
                        "severity": "high",
                        "detail":   f"Connection to suspicious IP range: {remote_ip}",
                        "ip":       remote_ip,
                        "time":     time.time(),
                    }
                    threats.append(threat)
                    self.anomaly_log.append(threat)

            # Log connection
            self.connection_log.append({
                "ip":     remote_ip,
                "port":   remote_port,
                "status": conn.status,
                "time":   time.time(),
            })

        # Update threat level
        if threats:
            high_count = sum(1 for t in threats if t.get("severity") == "high")
            self.threat_level = min(10, self.threat_level + high_count * 2)
            self.active_threats = threats
        else:
            self.threat_level = max(0, self.threat_level - 1)
            self.active_threats = []

        return threats

    def _fire_threat(self, threat: dict):
        for cb in self._callbacks:
            try:
                cb(threat)
            except Exception:
                pass

    def _load_threat_db(self):
        if os.path.exists(THREAT_DB_FILE):
            try:
                with open(THREAT_DB_FILE) as f:
                    data = json.load(f)
                self.blocked_ips = set(data.get("blocked_ips", []))
            except Exception:
                pass


# ── Singleton ─────────────────────────────────────────────────────────────────
_defense = CyberDefenseSystem()

def get_defense() -> CyberDefenseSystem:
    return _defense
