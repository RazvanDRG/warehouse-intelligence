"""Kafka consumer settings, read from KAFKA_* environment variables."""

from collections.abc import Callable
from typing import Any, Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# The System 1 topics WI reads (docs/architecture.md section 4).
WAREHOUSE_TOPICS = ["wms.stock.reserved", "wms.stock.released", "wms.pick.completed", "wms.order.audit"]


def default_ssl_context(cafile: str):
    from aiokafka.helpers import create_ssl_context

    return create_ssl_context(cafile=cafile)


class KafkaSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KAFKA_", env_file=".env", extra="ignore")

    bootstrap_servers: str = "localhost:9092"
    # No default: a local run sharing the deployed reader's group would take its messages.
    group_id: str = ""
    topics: list[str] = Field(default_factory=lambda: list(WAREHOUSE_TOPICS))
    # A new consumer group starts from the oldest kept message, so nothing published before it is missed.
    auto_offset_reset: Literal["earliest", "latest"] = "earliest"
    # PLAINTEXT for a local broker; SASL_SSL (login plus encryption) for Aiven.
    security_protocol: Literal["PLAINTEXT", "SASL_SSL"] = "PLAINTEXT"
    # PLAIN, like System 1's producer on the same Aiven cluster; the password still travels inside TLS.
    sasl_mechanism: Literal["PLAIN", "SCRAM-SHA-256", "SCRAM-SHA-512"] = "PLAIN"
    sasl_username: str = ""
    sasl_password: SecretStr = SecretStr("")
    # Path to the Aiven CA certificate file.
    ssl_cafile: str = ""

    def consumer_kwargs(self, ssl_context_factory: Callable[[str], Any] = default_ssl_context) -> dict[str, Any]:
        """Keyword arguments for AIOKafkaConsumer. Offsets are committed by hand, never automatically."""
        if not self.group_id.strip():
            raise ValueError("KAFKA_GROUP_ID is required: give every deployment and every local run its own group")
        kwargs: dict[str, Any] = {
            "bootstrap_servers": self.bootstrap_servers,
            "group_id": self.group_id,
            "enable_auto_commit": False,
            "auto_offset_reset": self.auto_offset_reset,
            "security_protocol": self.security_protocol,
        }
        if self.security_protocol == "SASL_SSL":
            missing = [
                name
                for name, value in (
                    ("sasl_username", self.sasl_username),
                    ("sasl_password", self.sasl_password.get_secret_value()),
                    ("ssl_cafile", self.ssl_cafile),
                )
                if not value
            ]
            if missing:
                raise ValueError(f"SASL_SSL needs KAFKA_ settings: {', '.join(missing)}")
            kwargs |= {
                "sasl_mechanism": self.sasl_mechanism,
                "sasl_plain_username": self.sasl_username,
                "sasl_plain_password": self.sasl_password.get_secret_value(),
                "ssl_context": ssl_context_factory(self.ssl_cafile),
            }
        return kwargs
