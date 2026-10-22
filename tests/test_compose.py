from pathlib import Path

import yaml

COMPOSE = Path(__file__).resolve().parent.parent / "infra" / "docker-compose.yml"
SYSTEM_1_HOST_PORTS = {"5432", "8000"}
EXPECTED_HOST_PORTS = {"api": "8001", "postgres": "5433", "redis": "6379", "prometheus": "9090", "grafana": "3000"}


def services() -> dict:
    return yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))["services"]


def host_ports(service: dict) -> set[str]:
    # "127.0.0.1:6379:6379" or "6379:6379": the host port is second to last.
    return {str(p).split(":")[-2] for p in service.get("ports", [])}


def test_compose_has_all_services_on_expected_ports():
    defined = services()
    for name, port in EXPECTED_HOST_PORTS.items():
        assert name in defined, f"missing service {name}"
        assert port in host_ports(defined[name]), f"{name} should publish host port {port}"


def test_postgres_has_pgvector():
    assert "pgvector" in services()["postgres"]["image"]


def test_ports_bound_to_localhost_only():
    for name, service in services().items():
        for port in service.get("ports", []):
            assert str(port).startswith("127.0.0.1:"), f"{name} publishes {port} on every network interface"


def test_no_port_clash_with_system_1():
    for name, service in services().items():
        assert not host_ports(service) & SYSTEM_1_HOST_PORTS, f"{name} uses a System 1 port"
