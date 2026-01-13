"""
Phase 5 Telemetry Standardization Tests

Tests cover:
- Spatial position detection and normalization
- Capabilities detection (has_spatial, has_events, has_metrics)
- Backward compatibility with existing telemetry data
- TelemetryIndex model functionality
- API response shape validation

Reference: Phase 5 - Telemetry Standardization + Spatial Replay Enablement
"""

import pytest
import uuid
from typing import Any, Dict

from app.services.telemetry import (
    TelemetryVersion,
    TelemetryCapabilities,
    NormalizedPosition,
    SPATIAL_X_ALIASES,
    SPATIAL_Y_ALIASES,
    SPATIAL_Z_ALIASES,
    extract_spatial_value,
    normalize_agent_position,
    extract_normalized_positions,
    detect_capabilities,
    _has_spatial_fields,
)
from app.models.telemetry_index import TelemetryIndex as TelemetryIndexModel


class TestSpatialFieldAliases:
    """Tests for spatial field alias constants."""

    def test_x_aliases_complete(self):
        """Test all X coordinate aliases are defined."""
        expected = ["x", "position_x", "pos_x", "coord_x", "loc_x"]
        assert SPATIAL_X_ALIASES == expected

    def test_y_aliases_complete(self):
        """Test all Y coordinate aliases are defined."""
        expected = ["y", "position_y", "pos_y", "coord_y", "loc_y"]
        assert SPATIAL_Y_ALIASES == expected

    def test_z_aliases_complete(self):
        """Test all Z coordinate aliases are defined."""
        expected = ["z", "position_z", "pos_z", "coord_z", "loc_z"]
        assert SPATIAL_Z_ALIASES == expected


class TestExtractSpatialValue:
    """Tests for extract_spatial_value function."""

    def test_extract_from_top_level_x(self):
        """Test extraction from top-level 'x' field."""
        state = {"x": 10.5, "y": 20.3}
        result = extract_spatial_value(state, SPATIAL_X_ALIASES)
        assert result == 10.5

    def test_extract_from_position_x(self):
        """Test extraction from 'position_x' field."""
        state = {"position_x": 15.0, "position_y": 25.0}
        result = extract_spatial_value(state, SPATIAL_X_ALIASES)
        assert result == 15.0

    def test_extract_from_nested_variables(self):
        """Test extraction from nested 'variables' dict."""
        state = {"variables": {"pos_x": 100.0, "pos_y": 200.0}}
        result = extract_spatial_value(state, SPATIAL_X_ALIASES)
        assert result == 100.0

    def test_top_level_takes_precedence(self):
        """Test that top-level fields take precedence over nested."""
        state = {
            "x": 10.0,
            "variables": {"x": 999.0}
        }
        result = extract_spatial_value(state, SPATIAL_X_ALIASES)
        assert result == 10.0

    def test_returns_default_when_not_found(self):
        """Test that default is returned when field not found."""
        state = {"other_field": 123}
        result = extract_spatial_value(state, SPATIAL_X_ALIASES, default=0.0)
        assert result == 0.0

    def test_returns_none_when_not_found_no_default(self):
        """Test that None is returned when field not found and no default."""
        state = {"other_field": 123}
        result = extract_spatial_value(state, SPATIAL_X_ALIASES)
        assert result is None

    def test_handles_integer_values(self):
        """Test that integer values are converted to float."""
        state = {"x": 10}  # integer
        result = extract_spatial_value(state, SPATIAL_X_ALIASES)
        assert result == 10.0
        assert isinstance(result, float)

    def test_ignores_non_numeric_values(self):
        """Test that non-numeric values are ignored."""
        state = {"x": "not a number", "pos_x": 5.0}
        result = extract_spatial_value(state, SPATIAL_X_ALIASES)
        assert result == 5.0


class TestNormalizeAgentPosition:
    """Tests for normalize_agent_position function."""

    def test_basic_xy_extraction(self):
        """Test basic x/y coordinate extraction."""
        pos = normalize_agent_position("agent_1", {"x": 10.0, "y": 20.0})
        assert pos is not None
        assert pos.agent_id == "agent_1"
        assert pos.x == 10.0
        assert pos.y == 20.0
        assert pos.z is None

    def test_position_xy_aliases(self):
        """Test position_x/position_y extraction."""
        pos = normalize_agent_position("agent_2", {"position_x": 30.0, "position_y": 40.0})
        assert pos is not None
        assert pos.x == 30.0
        assert pos.y == 40.0

    def test_xyz_extraction(self):
        """Test x/y/z coordinate extraction."""
        pos = normalize_agent_position("agent_3", {"x": 1.0, "y": 2.0, "z": 3.0})
        assert pos is not None
        assert pos.z == 3.0

    def test_rotation_and_scale(self):
        """Test rotation and scale extraction."""
        state = {"x": 0.0, "y": 0.0, "rotation": 45.0, "scale": 1.5}
        pos = normalize_agent_position("agent_4", state)
        assert pos is not None
        assert pos.rotation == 45.0
        assert pos.scale == 1.5

    def test_nested_variables_extraction(self):
        """Test extraction from nested variables."""
        state = {"variables": {"x": 50.0, "y": 60.0}}
        pos = normalize_agent_position("agent_5", state)
        assert pos is not None
        assert pos.x == 50.0
        assert pos.y == 60.0

    def test_grid_cell_fallback(self):
        """Test grid_cell fallback when no x/y available."""
        state = {"grid_cell": "A1"}
        pos = normalize_agent_position("agent_6", state)
        assert pos is not None
        assert pos.x == 0.0
        assert pos.y == 0.0
        assert pos.grid_cell == "A1"

    def test_location_id_fallback(self):
        """Test location_id fallback when no x/y available."""
        state = {"location_id": "zone_1"}
        pos = normalize_agent_position("agent_7", state)
        assert pos is not None
        assert pos.x == 0.0
        assert pos.y == 0.0
        assert pos.location_id == "zone_1"

    def test_returns_none_when_no_spatial_data(self):
        """Test that None is returned when no spatial data found."""
        state = {"name": "test", "status": "active"}
        pos = normalize_agent_position("agent_8", state)
        assert pos is None

    def test_mixed_aliases(self):
        """Test mixing different alias patterns."""
        state = {"pos_x": 100.0, "coord_y": 200.0}
        pos = normalize_agent_position("agent_9", state)
        assert pos is not None
        assert pos.x == 100.0
        assert pos.y == 200.0

    def test_to_dict_method(self):
        """Test NormalizedPosition.to_dict() method."""
        pos = NormalizedPosition(
            agent_id="test",
            x=10.0,
            y=20.0,
            z=30.0,
            rotation=90.0,
            grid_cell="B2",
        )
        d = pos.to_dict()
        assert d["agent_id"] == "test"
        assert d["x"] == 10.0
        assert d["y"] == 20.0
        assert d["z"] == 30.0
        assert d["rotation"] == 90.0
        assert d["grid_cell"] == "B2"
        assert "scale" not in d  # None values excluded


class TestExtractNormalizedPositions:
    """Tests for extract_normalized_positions function."""

    def test_extracts_multiple_agents(self):
        """Test extraction from multiple agents."""
        agent_states = {
            "agent_1": {"x": 10.0, "y": 20.0},
            "agent_2": {"x": 30.0, "y": 40.0},
            "agent_3": {"x": 50.0, "y": 60.0},
        }
        positions = extract_normalized_positions(agent_states)
        assert len(positions) == 3

    def test_filters_agents_without_spatial_data(self):
        """Test that agents without spatial data are filtered out."""
        agent_states = {
            "agent_1": {"x": 10.0, "y": 20.0},
            "agent_2": {"name": "no position"},
            "agent_3": {"position_x": 50.0, "position_y": 60.0},
        }
        positions = extract_normalized_positions(agent_states)
        assert len(positions) == 2

    def test_handles_empty_dict(self):
        """Test handling of empty agent states."""
        positions = extract_normalized_positions({})
        assert positions == []

    def test_handles_non_dict_values(self):
        """Test handling of non-dict values in agent states."""
        agent_states = {
            "agent_1": {"x": 10.0, "y": 20.0},
            "agent_2": "not a dict",
            "agent_3": None,
        }
        positions = extract_normalized_positions(agent_states)
        assert len(positions) == 1


class TestHasSpatialFields:
    """Tests for _has_spatial_fields function."""

    def test_detects_x_y(self):
        """Test detection of x/y fields."""
        assert _has_spatial_fields({"x": 0, "y": 0}) is True

    def test_detects_position_xy(self):
        """Test detection of position_x/position_y fields."""
        assert _has_spatial_fields({"position_x": 0, "position_y": 0}) is True

    def test_detects_nested_coordinates(self):
        """Test detection of coordinates in nested variables."""
        state = {"variables": {"pos_x": 0, "pos_y": 0}}
        assert _has_spatial_fields(state) is True

    def test_requires_both_x_and_y(self):
        """Test that both x and y must be present."""
        assert _has_spatial_fields({"x": 0}) is False
        assert _has_spatial_fields({"y": 0}) is False

    def test_grid_cell_fallback(self):
        """Test grid_cell detection as fallback."""
        assert _has_spatial_fields({"grid_cell": "A1"}) is True

    def test_location_id_fallback(self):
        """Test location_id detection as fallback."""
        assert _has_spatial_fields({"location_id": "zone_1"}) is True

    def test_no_spatial_data(self):
        """Test returns False when no spatial data."""
        assert _has_spatial_fields({"name": "test"}) is False


class TestTelemetryCapabilities:
    """Tests for TelemetryCapabilities class."""

    def test_default_values(self):
        """Test default capability values."""
        caps = TelemetryCapabilities()
        assert caps.has_spatial is False
        assert caps.has_events is False
        assert caps.has_metrics is False

    def test_to_dict(self):
        """Test to_dict method."""
        caps = TelemetryCapabilities(has_spatial=True, has_events=True, has_metrics=False)
        d = caps.to_dict()
        assert d == {
            "has_spatial": True,
            "has_events": True,
            "has_metrics": False,
        }

    def test_from_dict(self):
        """Test from_dict class method."""
        data = {"has_spatial": True, "has_events": False, "has_metrics": True}
        caps = TelemetryCapabilities.from_dict(data)
        assert caps.has_spatial is True
        assert caps.has_events is False
        assert caps.has_metrics is True

    def test_from_dict_with_missing_fields(self):
        """Test from_dict with missing fields defaults to False."""
        caps = TelemetryCapabilities.from_dict({})
        assert caps.has_spatial is False
        assert caps.has_events is False
        assert caps.has_metrics is False


class TestDetectCapabilities:
    """Tests for detect_capabilities function."""

    def test_detects_spatial_in_keyframes(self):
        """Test spatial detection from keyframes."""
        blob = {
            "keyframes": [
                {
                    "tick": 0,
                    "agent_states": {
                        "agent_1": {"x": 10.0, "y": 20.0}
                    }
                }
            ],
            "deltas": [],
            "final_states": {},
        }
        caps = detect_capabilities(blob)
        assert caps.has_spatial is True

    def test_detects_spatial_in_final_states(self):
        """Test spatial detection from final_states."""
        blob = {
            "keyframes": [],
            "deltas": [],
            "final_states": {
                "agent_1": {"position_x": 10.0, "position_y": 20.0}
            },
        }
        caps = detect_capabilities(blob)
        assert caps.has_spatial is True

    def test_detects_events_in_deltas(self):
        """Test event detection from deltas."""
        blob = {
            "keyframes": [],
            "deltas": [
                {"tick": 1, "events": ["event_1", "event_2"]},
            ],
            "final_states": {},
        }
        caps = detect_capabilities(blob)
        assert caps.has_events is True

    def test_detects_metrics_in_deltas(self):
        """Test metrics detection from deltas."""
        blob = {
            "keyframes": [],
            "deltas": [
                {"tick": 1, "metrics": {"sales": 100.0}},
            ],
            "final_states": {},
        }
        caps = detect_capabilities(blob)
        assert caps.has_metrics is True

    def test_empty_blob_returns_false_all(self):
        """Test empty blob returns all False capabilities."""
        blob = {"keyframes": [], "deltas": [], "final_states": {}}
        caps = detect_capabilities(blob)
        assert caps.has_spatial is False
        assert caps.has_events is False
        assert caps.has_metrics is False

    def test_full_capabilities_detection(self):
        """Test detection of all capabilities."""
        blob = {
            "keyframes": [
                {
                    "tick": 0,
                    "agent_states": {
                        "agent_1": {"x": 10.0, "y": 20.0}
                    }
                }
            ],
            "deltas": [
                {
                    "tick": 1,
                    "events": ["purchase"],
                    "metrics": {"revenue": 50.0}
                },
            ],
            "final_states": {},
        }
        caps = detect_capabilities(blob)
        assert caps.has_spatial is True
        assert caps.has_events is True
        assert caps.has_metrics is True


class TestTelemetryIndexModel:
    """Tests for TelemetryIndex database model."""

    def test_from_telemetry_blob_basic(self):
        """Test creating TelemetryIndex from basic blob."""
        tenant_id = uuid.uuid4()
        run_id = uuid.uuid4()
        blob = {
            "ticks_executed": 100,
            "agent_count": 50,
            "keyframes": [
                {"tick": 0, "agent_states": {}},
                {"tick": 50, "agent_states": {}},
            ],
            "deltas": [],
            "final_states": {"agent_1": {}, "agent_2": {}},
            "metrics_summary": {"total_sales": 1000},
            "schema_version": "v1",
        }

        index = TelemetryIndexModel.from_telemetry_blob(tenant_id, run_id, blob)

        assert index.tenant_id == tenant_id
        assert index.run_id == run_id
        assert index.total_ticks == 100
        assert index.total_agents == 50
        assert index.keyframe_ticks == [0, 50]
        assert "agent_1" in index.agent_ids
        assert "agent_2" in index.agent_ids

    def test_from_telemetry_blob_with_spatial(self):
        """Test TelemetryIndex detects spatial capabilities."""
        tenant_id = uuid.uuid4()
        run_id = uuid.uuid4()
        blob = {
            "ticks_executed": 10,
            "agent_count": 1,
            "keyframes": [
                {
                    "tick": 0,
                    "agent_states": {
                        "agent_1": {"x": 10.0, "y": 20.0}
                    }
                }
            ],
            "deltas": [],
            "final_states": {},
        }

        index = TelemetryIndexModel.from_telemetry_blob(tenant_id, run_id, blob)

        assert index.capabilities["has_spatial"] is True

    def test_from_telemetry_blob_with_events(self):
        """Test TelemetryIndex detects event capabilities."""
        tenant_id = uuid.uuid4()
        run_id = uuid.uuid4()
        blob = {
            "ticks_executed": 10,
            "agent_count": 0,
            "keyframes": [],
            "deltas": [
                {"tick": 1, "events": ["event_1"]}
            ],
            "final_states": {},
        }

        index = TelemetryIndexModel.from_telemetry_blob(tenant_id, run_id, blob)

        assert index.capabilities["has_events"] is True
        assert index.total_events == 1

    def test_from_telemetry_blob_with_metrics(self):
        """Test TelemetryIndex extracts metric keys."""
        tenant_id = uuid.uuid4()
        run_id = uuid.uuid4()
        blob = {
            "ticks_executed": 10,
            "agent_count": 0,
            "keyframes": [],
            "deltas": [
                {"tick": 1, "metrics": {"sales": 100, "revenue": 50}}
            ],
            "final_states": {},
            "metrics_summary": {"total": 500},
        }

        index = TelemetryIndexModel.from_telemetry_blob(tenant_id, run_id, blob)

        assert index.capabilities["has_metrics"] is True
        assert "total" in index.metric_keys
        assert "sales" in index.metric_keys
        assert "revenue" in index.metric_keys

    def test_to_api_response(self):
        """Test to_api_response method."""
        tenant_id = uuid.uuid4()
        run_id = uuid.uuid4()
        blob = {
            "ticks_executed": 100,
            "agent_count": 10,
            "keyframes": [{"tick": 0, "agent_states": {"a1": {"x": 1, "y": 2}}}],
            "deltas": [{"tick": 1, "events": ["e1"], "metrics": {"m1": 10}}],
            "final_states": {"a1": {}},
            "schema_version": "v1",
        }

        index = TelemetryIndexModel.from_telemetry_blob(tenant_id, run_id, blob)
        response = index.to_api_response()

        assert response["run_id"] == str(run_id)
        assert response["total_ticks"] == 100
        assert response["total_agents"] == 10
        assert "capabilities" in response
        assert response["capabilities"]["has_spatial"] is True
        assert response["capabilities"]["has_events"] is True
        assert response["capabilities"]["has_metrics"] is True


class TestTelemetryVersion:
    """Tests for TelemetryVersion enum."""

    def test_current_version(self):
        """Test current version is 1.1.0 (Phase 5)."""
        assert TelemetryVersion.CURRENT.value == "1.1.0"

    def test_version_values(self):
        """Test all version values exist."""
        assert TelemetryVersion.V1_0_0.value == "1.0.0"
        assert TelemetryVersion.V1_1_0.value == "1.1.0"


class TestBackwardCompatibility:
    """Tests for backward compatibility with existing telemetry data."""

    def test_blob_without_schema_version(self):
        """Test handling blob without schema_version defaults to v1."""
        tenant_id = uuid.uuid4()
        run_id = uuid.uuid4()
        blob = {
            "ticks_executed": 10,
            "agent_count": 5,
            "keyframes": [],
            "deltas": [],
            "final_states": {},
            # No schema_version field
        }

        index = TelemetryIndexModel.from_telemetry_blob(tenant_id, run_id, blob)
        assert index.schema_version == "v1"

    def test_blob_without_capabilities_fields(self):
        """Test handling blob without spatial/event/metric data."""
        tenant_id = uuid.uuid4()
        run_id = uuid.uuid4()
        blob = {
            "ticks_executed": 10,
            "agent_count": 5,
            "keyframes": [],
            "deltas": [],
            "final_states": {},
        }

        index = TelemetryIndexModel.from_telemetry_blob(tenant_id, run_id, blob)

        # All capabilities should be False for legacy data
        assert index.capabilities["has_spatial"] is False
        assert index.capabilities["has_events"] is False
        assert index.capabilities["has_metrics"] is False

    def test_legacy_agent_state_format(self):
        """Test handling legacy agent state format without nested variables."""
        state = {
            "id": "agent_1",
            "name": "Test Agent",
            "x": 100.0,
            "y": 200.0,
        }
        pos = normalize_agent_position("agent_1", state)
        assert pos is not None
        assert pos.x == 100.0
        assert pos.y == 200.0

    def test_mixed_format_agent_states(self):
        """Test handling mix of old and new format agent states."""
        agent_states = {
            # New format with nested variables
            "new_agent": {
                "variables": {"x": 10.0, "y": 20.0}
            },
            # Old format with top-level coordinates
            "old_agent": {
                "x": 30.0,
                "y": 40.0
            },
        }
        positions = extract_normalized_positions(agent_states)
        assert len(positions) == 2

    def test_empty_keyframes_and_deltas(self):
        """Test handling completely empty telemetry data."""
        blob = {
            "keyframes": [],
            "deltas": [],
            "final_states": {},
        }
        caps = detect_capabilities(blob)
        assert caps.has_spatial is False
        assert caps.has_events is False
        assert caps.has_metrics is False


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_negative_coordinates(self):
        """Test handling negative coordinate values."""
        pos = normalize_agent_position("agent", {"x": -100.0, "y": -200.0})
        assert pos is not None
        assert pos.x == -100.0
        assert pos.y == -200.0

    def test_zero_coordinates(self):
        """Test handling zero coordinate values."""
        pos = normalize_agent_position("agent", {"x": 0.0, "y": 0.0})
        assert pos is not None
        assert pos.x == 0.0
        assert pos.y == 0.0

    def test_very_large_coordinates(self):
        """Test handling very large coordinate values."""
        pos = normalize_agent_position("agent", {"x": 1e10, "y": 1e10})
        assert pos is not None
        assert pos.x == 1e10

    def test_float_precision(self):
        """Test handling floating point precision."""
        pos = normalize_agent_position("agent", {"x": 0.123456789, "y": 0.987654321})
        assert pos is not None
        assert abs(pos.x - 0.123456789) < 1e-9

    def test_empty_variables_dict(self):
        """Test handling empty variables dict."""
        state = {"variables": {}, "x": 10.0, "y": 20.0}
        pos = normalize_agent_position("agent", state)
        assert pos is not None

    def test_non_dict_variables(self):
        """Test handling non-dict variables field."""
        state = {"variables": "not a dict", "x": 10.0, "y": 20.0}
        pos = normalize_agent_position("agent", state)
        assert pos is not None

    def test_unicode_agent_id(self):
        """Test handling unicode agent IDs."""
        pos = normalize_agent_position("エージェント_1", {"x": 10.0, "y": 20.0})
        assert pos is not None
        assert pos.agent_id == "エージェント_1"

    def test_special_characters_in_location_id(self):
        """Test handling special characters in location_id."""
        state = {"location_id": "zone/1/area-2"}
        pos = normalize_agent_position("agent", state)
        assert pos is not None
        assert pos.location_id == "zone/1/area-2"
