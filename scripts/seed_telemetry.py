#!/usr/bin/env python3
"""Seed telemetry data for energy reporting devices."""

import random
from datetime import datetime, timedelta
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = "energy-token"
INFLUX_ORG = "energy-org"
INFLUX_BUCKET = "telemetry"
MEASUREMENT = "device_telemetry"

def get_write_client():
    return InfluxDBClient(
        url=INFLUX_URL,
        token=INFLUX_TOKEN,
        org=INFLUX_ORG
    )

def seed_device_data(device_id: str, phase_type: str, days: int = 7):
    """Seed telemetry data for a device for given number of days."""
    
    # Base values based on phase type
    if phase_type == "three":
        base_voltage = 415  # Three-phase voltage (V)
        base_current = random.uniform(50, 150)  # Amps
        power_factor = random.uniform(0.75, 0.95)
    else:
        base_voltage = 230  # Single-phase voltage (V)
        base_current = random.uniform(10, 30)  # Amps
        power_factor = random.uniform(0.80, 0.95)
    
    # Calculate base power
    if phase_type == "three":
        base_power = 1.732 * base_voltage * base_current * power_factor / 1000  # kW
    else:
        base_power = base_voltage * base_current * power_factor / 1000  # kW
    
    print(f"Seeding {days} days of data for {device_id} ({phase_type}-phase)")
    print(f"  Base: {base_voltage}V, {base_current:.1f}A, PF={power_factor:.2f}, Power={base_power:.1f}kW")
    
    client = get_write_client()
    write_api = client.write_api(write_options=SYNCHRONOUS)
    
    points = []
    now = datetime.utcnow()
    start_time = now - timedelta(days=days)
    
    # Generate data points every 15 minutes for the entire period
    current_time = start_time
    total_points = 0
    
    while current_time <= now:
        # Add some variation to the values
        voltage_var = random.uniform(-10, 10)
        current_var = base_current * random.uniform(-0.15, 0.15)
        pf_var = power_factor * random.uniform(-0.05, 0.05)
        
        voltage = base_voltage + voltage_var
        current = max(0.1, base_current + current_var)
        pf = max(0.5, min(1.0, power_factor + pf_var))
        
        # Calculate power
        if phase_type == "three":
            power = 1.732 * voltage * current * pf / 1000  # kW
        else:
            power = voltage * current * pf / 1000  # kW
        
        # Add time-of-day variation (higher during working hours)
        hour = current_time.hour
        if 9 <= hour <= 17:  # Working hours
            multiplier = 1.0 + random.uniform(0, 0.3)
        elif 6 <= hour <= 22:  # Day time
            multiplier = 0.7 + random.uniform(-0.1, 0.1)
        else:  # Night
            multiplier = 0.3 + random.uniform(-0.1, 0.1)
        
        power = power * multiplier
        current = current * multiplier
        
        # Reactive power (VAR)
        apparent_power = power / pf if pf > 0 else power
        reactive_power = (apparent_power ** 2 - power ** 2) ** 0.5
        
        # Frequency (Hz)
        frequency = 50.0 + random.uniform(-0.5, 0.5)
        
        # THD (%)
        thd = random.uniform(2, 8)
        
        # Create point
        point = (
            Point(MEASUREMENT)
            .tag("device_id", device_id)
            .field("voltage", round(voltage, 2))
            .field("current", round(current, 2))
            .field("power_factor", round(pf, 3))
            .field("power", round(power, 2))
            .field("reactive_power", round(reactive_power, 2))
            .field("frequency", round(frequency, 2))
            .field("thd", round(thd, 2))
            .time(current_time)
        )
        
        points.append(point)
        
        # Write in batches of 100
        if len(points) >= 100:
            write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=points)
            total_points += len(points)
            print(f"  Written {total_points} points...")
            points = []
        
        # Move to next 15-minute interval
        current_time += timedelta(minutes=15)
    
    # Write remaining points
    if points:
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=points)
        total_points += len(points)
    
    print(f"  Total: {total_points} points written")
    client.close()
    return total_points

def main():
    print("=" * 60)
    print("Seeding telemetry data for energy reports")
    print("=" * 60)
    
    # Seed data for each device
    devices = [
        ("D2", "three"),           # Device 2 - Power Monitor (existing)
        ("POWER-001", "three"),    # Main Power Meter
        ("POWER-002", "three"),    # Industrial Motor
        ("POWER-003", "single"),   # HVAC System
    ]
    
    for device_id, phase_type in devices:
        try:
            seed_device_data(device_id, phase_type, days=7)
            print()
        except Exception as e:
            print(f"Error seeding {device_id}: {e}")
    
    print("=" * 60)
    print("Done! All devices seeded with 7 days of data.")
    print("=" * 60)

if __name__ == "__main__":
    main()
