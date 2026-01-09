"""
2D Layout Profiles Service
Reference: project.md §11 Phase 8

Defines layout profiles per domain template with semantic zones.
- Layout profile defines zones (regions) on canvas
- Agents placed in zones based on segment
- Layout configurable per domain template
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import math


class LayoutType(str, Enum):
    """Types of layout algorithms."""
    GRID = "grid"           # Regular grid arrangement
    RADIAL = "radial"       # Circular/radial arrangement
    CLUSTER = "cluster"     # Clustered by segment
    GEOGRAPHIC = "geographic"  # Map-based (requires coordinates)
    FLOW = "flow"           # Left-to-right flow
    FORCE = "force"         # Force-directed layout


class ZoneShape(str, Enum):
    """Shapes for semantic zones."""
    RECTANGLE = "rectangle"
    CIRCLE = "circle"
    POLYGON = "polygon"
    ORGANIC = "organic"  # Irregular, flowing shape


@dataclass
class ZoneDefinition:
    """
    Defines a semantic zone on the canvas.
    Zones represent regions or segments where agents are placed.
    """
    zone_id: str
    name: str
    shape: ZoneShape
    bounds: Dict[str, float]  # x, y, width, height (or radius for circle)
    color: str  # Hex color for zone background
    border_color: str
    segments: List[str]  # Which segments belong to this zone
    regions: List[str]  # Which regions this zone represents
    label_position: Dict[str, float]  # x, y for label
    capacity: Optional[int] = None  # Max agents (for layout optimization)
    priority: int = 0  # Higher priority zones rendered on top

    def to_dict(self) -> dict:
        return {
            "zone_id": self.zone_id,
            "name": self.name,
            "shape": self.shape.value,
            "bounds": self.bounds,
            "color": self.color,
            "border_color": self.border_color,
            "segments": self.segments,
            "regions": self.regions,
            "label_position": self.label_position,
            "capacity": self.capacity,
            "priority": self.priority,
        }


@dataclass
class AgentVisualConfig:
    """
    Configuration for how agents are visualized.
    """
    base_size: float = 8.0  # Base agent sprite size
    min_size: float = 4.0
    max_size: float = 16.0
    size_by: Optional[str] = None  # Variable to scale size (e.g., "influence")
    shape: str = "circle"  # circle, square, triangle
    show_label: bool = False
    label_field: str = "agent_id"
    spacing: float = 12.0  # Minimum spacing between agents

    def to_dict(self) -> dict:
        return {
            "base_size": self.base_size,
            "min_size": self.min_size,
            "max_size": self.max_size,
            "size_by": self.size_by,
            "shape": self.shape,
            "show_label": self.show_label,
            "label_field": self.label_field,
            "spacing": self.spacing,
        }


@dataclass
class LayoutProfile:
    """
    Complete layout profile for a domain template.
    Defines how the 2D canvas is structured and how agents are positioned.
    """
    profile_id: str
    name: str
    domain_template: str
    layout_type: LayoutType
    canvas_width: int
    canvas_height: int
    background_color: str
    zones: List[ZoneDefinition]
    agent_config: AgentVisualConfig
    grid_lines: bool = False
    show_legend: bool = True
    legend_position: str = "bottom-right"  # top-left, top-right, bottom-left, bottom-right
    animation_speed: float = 1.0  # Playback speed multiplier
    default_zoom: float = 1.0
    min_zoom: float = 0.1
    max_zoom: float = 5.0

    def to_dict(self) -> dict:
        return {
            "profile_id": self.profile_id,
            "name": self.name,
            "domain_template": self.domain_template,
            "layout_type": self.layout_type.value,
            "canvas_width": self.canvas_width,
            "canvas_height": self.canvas_height,
            "background_color": self.background_color,
            "zones": [z.to_dict() for z in self.zones],
            "agent_config": self.agent_config.to_dict(),
            "grid_lines": self.grid_lines,
            "show_legend": self.show_legend,
            "legend_position": self.legend_position,
            "animation_speed": self.animation_speed,
            "default_zoom": self.default_zoom,
            "min_zoom": self.min_zoom,
            "max_zoom": self.max_zoom,
        }

    def get_zone_for_agent(
        self,
        segment: str,
        region: Optional[str] = None,
    ) -> Optional[ZoneDefinition]:
        """Find the zone for an agent based on segment and region."""
        for zone in self.zones:
            # Check if segment matches
            if segment in zone.segments:
                # If region is specified, also check region
                if region and zone.regions:
                    if region in zone.regions:
                        return zone
                else:
                    return zone

            # Check if region matches (fallback)
            if region and region in zone.regions:
                return zone

        # Return first zone as fallback
        return self.zones[0] if self.zones else None


@dataclass
class AgentPosition:
    """
    Calculated position for an agent on the canvas.
    """
    agent_id: str
    x: float
    y: float
    zone_id: str
    size: float
    rotation: float = 0.0

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "x": self.x,
            "y": self.y,
            "zone_id": self.zone_id,
            "size": self.size,
            "rotation": self.rotation,
        }


class LayoutCalculator:
    """
    Calculates agent positions based on layout profile.
    """

    def __init__(self, profile: LayoutProfile):
        self.profile = profile

    def calculate_positions(
        self,
        agents: List[Dict[str, Any]],
    ) -> List[AgentPosition]:
        """
        Calculate positions for all agents based on layout type.

        Args:
            agents: List of agent state dictionaries with segment/region info

        Returns:
            List of AgentPosition objects
        """
        layout_type = self.profile.layout_type

        if layout_type == LayoutType.GRID:
            return self._calculate_grid_positions(agents)
        elif layout_type == LayoutType.RADIAL:
            return self._calculate_radial_positions(agents)
        elif layout_type == LayoutType.CLUSTER:
            return self._calculate_cluster_positions(agents)
        elif layout_type == LayoutType.FLOW:
            return self._calculate_flow_positions(agents)
        else:
            # Default to grid
            return self._calculate_grid_positions(agents)

    def _calculate_grid_positions(
        self,
        agents: List[Dict[str, Any]],
    ) -> List[AgentPosition]:
        """Arrange agents in a grid within their zones."""
        positions = []
        zone_agents: Dict[str, List[Dict[str, Any]]] = {}

        # Group agents by zone
        for agent in agents:
            segment = agent.get("segment", "default")
            region = agent.get("region")
            zone = self.profile.get_zone_for_agent(segment, region)

            if zone:
                if zone.zone_id not in zone_agents:
                    zone_agents[zone.zone_id] = []
                zone_agents[zone.zone_id].append(agent)

        # Position agents within each zone
        for zone in self.profile.zones:
            zone_agent_list = zone_agents.get(zone.zone_id, [])
            if not zone_agent_list:
                continue

            bounds = zone.bounds
            spacing = self.profile.agent_config.spacing
            base_size = self.profile.agent_config.base_size

            # Calculate grid dimensions
            zone_width = bounds.get("width", 100)
            zone_height = bounds.get("height", 100)
            zone_x = bounds.get("x", 0)
            zone_y = bounds.get("y", 0)

            cols = max(1, int(zone_width / spacing))
            rows = max(1, int(zone_height / spacing))

            for i, agent in enumerate(zone_agent_list):
                row = i // cols
                col = i % cols

                # Wrap to next row if needed
                if row >= rows:
                    row = row % rows
                    col = (col + 1) % cols

                x = zone_x + (col + 0.5) * spacing
                y = zone_y + (row + 0.5) * spacing

                # Calculate size based on config
                size = self._calculate_agent_size(agent)

                positions.append(AgentPosition(
                    agent_id=agent.get("agent_id", agent.get("id", "")),
                    x=x,
                    y=y,
                    zone_id=zone.zone_id,
                    size=size,
                ))

        return positions

    def _calculate_radial_positions(
        self,
        agents: List[Dict[str, Any]],
    ) -> List[AgentPosition]:
        """Arrange agents in concentric circles by zone."""
        positions = []

        for zone in self.profile.zones:
            zone_agents = [
                a for a in agents
                if self.profile.get_zone_for_agent(
                    a.get("segment", "default"),
                    a.get("region")
                ) == zone
            ]

            if not zone_agents:
                continue

            bounds = zone.bounds
            center_x = bounds.get("x", 0) + bounds.get("width", 100) / 2
            center_y = bounds.get("y", 0) + bounds.get("height", 100) / 2
            max_radius = min(bounds.get("width", 100), bounds.get("height", 100)) / 2

            # Arrange in concentric circles
            agents_per_ring = 8
            ring = 0
            ring_offset = 0

            for i, agent in enumerate(zone_agents):
                if ring_offset >= agents_per_ring * (ring + 1):
                    ring += 1
                    ring_offset = 0

                angle = (ring_offset / (agents_per_ring * (ring + 1))) * 2 * math.pi
                radius = (ring + 1) * (max_radius / 5)  # 5 rings max

                x = center_x + radius * math.cos(angle)
                y = center_y + radius * math.sin(angle)

                size = self._calculate_agent_size(agent)

                positions.append(AgentPosition(
                    agent_id=agent.get("agent_id", agent.get("id", "")),
                    x=x,
                    y=y,
                    zone_id=zone.zone_id,
                    size=size,
                ))

                ring_offset += 1

        return positions

    def _calculate_cluster_positions(
        self,
        agents: List[Dict[str, Any]],
    ) -> List[AgentPosition]:
        """Cluster agents by segment with organic spacing."""
        # Use grid as base but with some random offset for organic feel
        return self._calculate_grid_positions(agents)

    def _calculate_flow_positions(
        self,
        agents: List[Dict[str, Any]],
    ) -> List[AgentPosition]:
        """Arrange agents in a left-to-right flow."""
        positions = []
        spacing = self.profile.agent_config.spacing

        for i, agent in enumerate(agents):
            segment = agent.get("segment", "default")
            region = agent.get("region")
            zone = self.profile.get_zone_for_agent(segment, region)

            if zone:
                bounds = zone.bounds
                zone_width = bounds.get("width", 100)
                cols = max(1, int(zone_width / spacing))

                row = i // cols
                col = i % cols

                x = bounds.get("x", 0) + (col + 0.5) * spacing
                y = bounds.get("y", 0) + (row + 0.5) * spacing

                size = self._calculate_agent_size(agent)

                positions.append(AgentPosition(
                    agent_id=agent.get("agent_id", agent.get("id", "")),
                    x=x,
                    y=y,
                    zone_id=zone.zone_id,
                    size=size,
                ))

        return positions

    def _calculate_agent_size(self, agent: Dict[str, Any]) -> float:
        """Calculate agent size based on config."""
        config = self.profile.agent_config

        if config.size_by and config.size_by in agent:
            value = agent[config.size_by]
            # Normalize to 0-1 range
            normalized = max(0, min(1, float(value)))
            size = config.min_size + normalized * (config.max_size - config.min_size)
            return size

        return config.base_size


# ============================================================
# Default Layout Profiles per Domain Template
# ============================================================

DEFAULT_PROFILES: Dict[str, LayoutProfile] = {
    "consumer": LayoutProfile(
        profile_id="consumer-default",
        name="Consumer Behavior Layout",
        domain_template="consumer",
        layout_type=LayoutType.CLUSTER,
        canvas_width=1200,
        canvas_height=800,
        background_color="#0a0a0f",
        zones=[
            ZoneDefinition(
                zone_id="early-adopters",
                name="Early Adopters",
                shape=ZoneShape.RECTANGLE,
                bounds={"x": 50, "y": 50, "width": 350, "height": 300},
                color="#1a1a2e",
                border_color="#00ffff",
                segments=["early_adopter", "innovator"],
                regions=[],
                label_position={"x": 175, "y": 30},
                priority=1,
            ),
            ZoneDefinition(
                zone_id="mainstream",
                name="Mainstream",
                shape=ZoneShape.RECTANGLE,
                bounds={"x": 425, "y": 50, "width": 350, "height": 300},
                color="#1a1a2e",
                border_color="#888888",
                segments=["mainstream", "early_majority", "late_majority"],
                regions=[],
                label_position={"x": 600, "y": 30},
                priority=0,
            ),
            ZoneDefinition(
                zone_id="laggards",
                name="Skeptics",
                shape=ZoneShape.RECTANGLE,
                bounds={"x": 800, "y": 50, "width": 350, "height": 300},
                color="#1a1a2e",
                border_color="#ff4444",
                segments=["laggard", "skeptic", "resistant"],
                regions=[],
                label_position={"x": 975, "y": 30},
                priority=0,
            ),
            ZoneDefinition(
                zone_id="influencers",
                name="Influencers",
                shape=ZoneShape.CIRCLE,
                bounds={"x": 450, "y": 450, "width": 300, "height": 300},
                color="#2a1a2e",
                border_color="#ff00ff",
                segments=["influencer", "opinion_leader"],
                regions=[],
                label_position={"x": 600, "y": 600},
                priority=2,
            ),
        ],
        agent_config=AgentVisualConfig(
            base_size=8,
            size_by="influence",
            shape="circle",
        ),
        show_legend=True,
        legend_position="bottom-right",
    ),

    "financial": LayoutProfile(
        profile_id="financial-default",
        name="Financial Decision Layout",
        domain_template="financial",
        layout_type=LayoutType.RADIAL,
        canvas_width=1000,
        canvas_height=1000,
        background_color="#0a0a0f",
        zones=[
            ZoneDefinition(
                zone_id="risk-seeking",
                name="Risk Seeking",
                shape=ZoneShape.CIRCLE,
                bounds={"x": 100, "y": 100, "width": 350, "height": 350},
                color="#2e1a1a",
                border_color="#ff4444",
                segments=["aggressive", "risk_seeking", "speculative"],
                regions=[],
                label_position={"x": 275, "y": 50},
                priority=0,
            ),
            ZoneDefinition(
                zone_id="balanced",
                name="Balanced",
                shape=ZoneShape.CIRCLE,
                bounds={"x": 325, "y": 325, "width": 350, "height": 350},
                color="#1a2e1a",
                border_color="#44ff44",
                segments=["balanced", "moderate", "diversified"],
                regions=[],
                label_position={"x": 500, "y": 275},
                priority=1,
            ),
            ZoneDefinition(
                zone_id="conservative",
                name="Conservative",
                shape=ZoneShape.CIRCLE,
                bounds={"x": 550, "y": 100, "width": 350, "height": 350},
                color="#1a1a2e",
                border_color="#4444ff",
                segments=["conservative", "risk_averse", "cautious"],
                regions=[],
                label_position={"x": 725, "y": 50},
                priority=0,
            ),
        ],
        agent_config=AgentVisualConfig(
            base_size=10,
            size_by="exposure",
            shape="circle",
        ),
        show_legend=True,
    ),

    "career": LayoutProfile(
        profile_id="career-default",
        name="Career Path Layout",
        domain_template="career",
        layout_type=LayoutType.FLOW,
        canvas_width=1400,
        canvas_height=600,
        background_color="#0a0a0f",
        zones=[
            ZoneDefinition(
                zone_id="entry",
                name="Entry Level",
                shape=ZoneShape.RECTANGLE,
                bounds={"x": 50, "y": 100, "width": 250, "height": 400},
                color="#1a1a2e",
                border_color="#00ffff",
                segments=["entry", "junior", "intern"],
                regions=[],
                label_position={"x": 175, "y": 80},
                priority=0,
            ),
            ZoneDefinition(
                zone_id="mid",
                name="Mid Level",
                shape=ZoneShape.RECTANGLE,
                bounds={"x": 350, "y": 100, "width": 300, "height": 400},
                color="#1a2e1a",
                border_color="#44ff44",
                segments=["mid", "intermediate", "experienced"],
                regions=[],
                label_position={"x": 500, "y": 80},
                priority=0,
            ),
            ZoneDefinition(
                zone_id="senior",
                name="Senior",
                shape=ZoneShape.RECTANGLE,
                bounds={"x": 700, "y": 100, "width": 300, "height": 400},
                color="#2e2e1a",
                border_color="#ffff44",
                segments=["senior", "lead", "principal"],
                regions=[],
                label_position={"x": 850, "y": 80},
                priority=0,
            ),
            ZoneDefinition(
                zone_id="executive",
                name="Executive",
                shape=ZoneShape.RECTANGLE,
                bounds={"x": 1050, "y": 100, "width": 300, "height": 400},
                color="#2e1a2e",
                border_color="#ff44ff",
                segments=["executive", "director", "vp", "c-level"],
                regions=[],
                label_position={"x": 1200, "y": 80},
                priority=1,
            ),
        ],
        agent_config=AgentVisualConfig(
            base_size=10,
            size_by="influence",
            shape="square",
        ),
        show_legend=True,
        legend_position="top-right",
    ),

    "default": LayoutProfile(
        profile_id="default",
        name="Default Grid Layout",
        domain_template="default",
        layout_type=LayoutType.GRID,
        canvas_width=1200,
        canvas_height=800,
        background_color="#0a0a0f",
        zones=[
            ZoneDefinition(
                zone_id="main",
                name="Agents",
                shape=ZoneShape.RECTANGLE,
                bounds={"x": 50, "y": 50, "width": 1100, "height": 700},
                color="#1a1a2e",
                border_color="#00ffff",
                segments=["default"],
                regions=[],
                label_position={"x": 600, "y": 30},
                priority=0,
            ),
        ],
        agent_config=AgentVisualConfig(),
        show_legend=True,
    ),
}


class LayoutProfileService:
    """
    Service for managing layout profiles.
    """

    def __init__(self):
        self.profiles: Dict[str, LayoutProfile] = dict(DEFAULT_PROFILES)

    def get_profile(self, domain_template: str) -> LayoutProfile:
        """Get layout profile for a domain template."""
        return self.profiles.get(domain_template, self.profiles["default"])

    def get_profile_by_id(self, profile_id: str) -> Optional[LayoutProfile]:
        """Get layout profile by ID."""
        for profile in self.profiles.values():
            if profile.profile_id == profile_id:
                return profile
        return None

    def list_profiles(self) -> List[LayoutProfile]:
        """List all available layout profiles."""
        return list(self.profiles.values())

    def register_profile(self, profile: LayoutProfile):
        """Register a custom layout profile."""
        self.profiles[profile.domain_template] = profile

    def calculate_positions(
        self,
        domain_template: str,
        agents: List[Dict[str, Any]],
    ) -> List[AgentPosition]:
        """Calculate agent positions using the appropriate layout."""
        profile = self.get_profile(domain_template)
        calculator = LayoutCalculator(profile)
        return calculator.calculate_positions(agents)


# Singleton instance
_layout_service: Optional[LayoutProfileService] = None


def get_layout_service() -> LayoutProfileService:
    """Get the layout profile service instance."""
    global _layout_service
    if _layout_service is None:
        _layout_service = LayoutProfileService()
    return _layout_service
