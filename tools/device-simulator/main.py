"""CLI entry point for device simulator."""
import argparse
import logging
import os
import sys
import json

from config import SimulatorConfig
from simulator import DeviceSimulator


def setup_logging(log_level: str) -> None:
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, log_level.upper()))

    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)

    if not logger.handlers:
        logger.addHandler(handler)

    if log_level.upper() != "DEBUG":
        logging.getLogger("paho").setLevel(logging.WARNING)


def parse_arguments() -> SimulatorConfig:
    """CLI + ENV compatible configuration with support for custom metrics."""

    env_device_id = os.getenv("DEVICE_ID")
    env_broker = os.getenv("MQTT_BROKER_HOST", "localhost")
    env_port = int(os.getenv("MQTT_BROKER_PORT", "1883"))
    env_interval = float(os.getenv("PUBLISH_INTERVAL", "5"))
    env_fault_mode = os.getenv("FAULT_MODE", "none")
    env_log_level = os.getenv("LOG_LEVEL", "INFO")
    env_metrics = os.getenv("METRICS", "")

    parser = argparse.ArgumentParser(
        description="Energy Intelligence Platform - Device Simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--device-id",
        type=str,
        default=env_device_id,
        help="Device identifier (env: DEVICE_ID)"
    )

    parser.add_argument(
        "--interval",
        type=float,
        default=env_interval,
        help="Publish interval in seconds (env: PUBLISH_INTERVAL)"
    )

    parser.add_argument(
        "--broker",
        type=str,
        default=env_broker,
        help="MQTT broker host (env: MQTT_BROKER_HOST)"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=env_port,
        help="MQTT broker port (env: MQTT_BROKER_PORT)"
    )

    parser.add_argument(
        "--fault-mode",
        type=str,
        default=env_fault_mode,
        choices=["none", "spike", "drop", "overheating"],
        help="Fault mode (env: FAULT_MODE)"
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default=env_log_level,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (env: LOG_LEVEL)"
    )

    parser.add_argument(
        "--metrics",
        type=str,
        default=env_metrics,
        help="Comma-separated list of metrics to generate (e.g., 'voltage,current,power,temperature') or JSON array (env: METRICS)"
    )

    parser.add_argument(
        "--metrics-json",
        type=str,
        default="",
        help="JSON object defining metrics with their ranges: '{\"pressure\": [0, 10], \"temperature\": [20, 100]}'"
    )

    args = parser.parse_args()

    if not args.device_id:
        raise ValueError(
            "device-id must be provided either via --device-id or DEVICE_ID env variable"
        )

    return SimulatorConfig(
        device_id=args.device_id,
        publish_interval=args.interval,
        broker_host=args.broker,
        broker_port=args.port,
        fault_mode=args.fault_mode,
        log_level=args.log_level,
        metrics=args.metrics,
        metrics_json=args.metrics_json,
    )


def main() -> int:
    try:
        config = parse_arguments()
        setup_logging(config.log_level)

        logging.getLogger(__name__).info(
            "Starting device simulator",
            extra={
                "device_id": config.device_id,
                "broker": config.broker_host,
                "port": config.broker_port,
                "topic": config.topic,
                "metrics": config.metrics,
            },
        )

        simulator = DeviceSimulator(config)
        simulator.start()

        return 0

    except ValueError as e:
        logging.error(f"Configuration error: {e}")
        return 1
    except KeyboardInterrupt:
        logging.info("Interrupted by user")
        return 0
    except Exception as e:
        logging.error("Unexpected error", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
