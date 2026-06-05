"""Tests for doser domain configuration logic."""

import pytest

from src.aquable.domain.doser import (
    Calibration,
    ConfigurationRevision,
    DeviceConfiguration,
    DoserHead,
    Recurrence,
    SingleSchedule,
)


def test_device_configuration_validation():
    head = DoserHead(
        index=1,
        active=True,
        schedule=SingleSchedule(dailyDoseMl=10.0, startTime="08:00"),
        recurrence=Recurrence(["monday"]),
        missedDoseCompensation=False,
        calibration=Calibration(mlPerSecond=1.0, lastCalibratedAt="2024-01-01"),
    )
    
    rev = ConfigurationRevision(
        revision=1,
        savedAt="2024-01-01",
        heads=[head]
    )
    
    config = DeviceConfiguration(
        id="config-1",
        name="Main",
        revisions=[rev],
        createdAt="2024-01-01",
        updatedAt="2024-01-01"
    )
    
    assert config.latest_revision().revision == 1

def test_device_configuration_invalid_revisions():
    head = DoserHead(
        index=1,
        active=True,
        schedule=SingleSchedule(dailyDoseMl=10.0, startTime="08:00"),
        recurrence=Recurrence(["monday"]),
        missedDoseCompensation=False,
        calibration=Calibration(mlPerSecond=1.0, lastCalibratedAt="2024-01-01"),
    )
    
    rev1 = ConfigurationRevision(revision=1, savedAt="2024-01-01", heads=[head])
    rev3 = ConfigurationRevision(revision=3, savedAt="2024-01-01", heads=[head])
    
    # Missing revision 2
    with pytest.raises(ValueError, match="Configuration revision numbers must increase sequentially"):
        DeviceConfiguration(
            id="config-1",
            name="Main",
            revisions=[rev1, rev3],
            createdAt="2024-01-01",
            updatedAt="2024-01-01"
        )
