"""
Rendering Mappings Service
Reference: project.md §11 Phase 8

State → Visual mapping rules for 2D Replay:
- Colors mapped to state dimensions
- Icons for agent types and actions
- Animations for state transitions
- Configurable per domain template
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Callable
import colorsys


class ColorScaleType(str, Enum):
    """Types of color scales."""
    LINEAR = "linear"           # Linear interpolation
    DIVERGING = "diverging"     # Two colors from center
    CATEGORICAL = "categorical"  # Discrete color categories
    THRESHOLD = "threshold"      # Step-based thresholds


class AnimationType(str, Enum):
    """Types of animations."""
    PULSE = "pulse"        # Size pulse effect
    GLOW = "glow"          # Glowing border
    SHAKE = "shake"        # Rapid shake
    FADE = "fade"          # Opacity change
    RIPPLE = "ripple"      # Expanding ring
    TRAIL = "trail"        # Motion trail
    NONE = "none"


@dataclass
class ColorScale:
    """
    Defines a color scale for mapping values to colors.
    """
    scale_type: ColorScaleType
    colors: List[str]  # Hex colors
    domain: Tuple[float, float] = (0.0, 1.0)  # Value range
    thresholds: Optional[List[float]] = None  # For threshold type

    def get_color(self, value: float) -> str:
        """Get color for a value."""
        # Normalize value to 0-1
        min_val, max_val = self.domain
        if max_val == min_val:
            normalized = 0.5
        else:
            normalized = (value - min_val) / (max_val - min_val)
        normalized = max(0, min(1, normalized))

        if self.scale_type == ColorScaleType.LINEAR:
            return self._linear_interpolate(normalized)
        elif self.scale_type == ColorScaleType.DIVERGING:
            return self._diverging_interpolate(normalized)
        elif self.scale_type == ColorScaleType.CATEGORICAL:
            return self._categorical_color(value)
        elif self.scale_type == ColorScaleType.THRESHOLD:
            return self._threshold_color(value)
        else:
            return self.colors[0] if self.colors else "#ffffff"

    def _linear_interpolate(self, t: float) -> str:
        """Linear interpolation between colors."""
        if len(self.colors) < 2:
            return self.colors[0] if self.colors else "#ffffff"

        # Find segment
        segment_count = len(self.colors) - 1
        segment = min(int(t * segment_count), segment_count - 1)
        local_t = (t * segment_count) - segment

        color1 = self._hex_to_rgb(self.colors[segment])
        color2 = self._hex_to_rgb(self.colors[segment + 1])

        r = int(color1[0] + (color2[0] - color1[0]) * local_t)
        g = int(color1[1] + (color2[1] - color1[1]) * local_t)
        b = int(color1[2] + (color2[2] - color1[2]) * local_t)

        return f"#{r:02x}{g:02x}{b:02x}"

    def _diverging_interpolate(self, t: float) -> str:
        """Diverging interpolation (negative-neutral-positive)."""
        if len(self.colors) < 3:
            return self._linear_interpolate(t)

        if t < 0.5:
            # Negative to neutral
            local_t = t * 2
            color1 = self._hex_to_rgb(self.colors[0])
            color2 = self._hex_to_rgb(self.colors[1])
        else:
            # Neutral to positive
            local_t = (t - 0.5) * 2
            color1 = self._hex_to_rgb(self.colors[1])
            color2 = self._hex_to_rgb(self.colors[2])

        r = int(color1[0] + (color2[0] - color1[0]) * local_t)
        g = int(color1[1] + (color2[1] - color1[1]) * local_t)
        b = int(color1[2] + (color2[2] - color1[2]) * local_t)

        return f"#{r:02x}{g:02x}{b:02x}"

    def _categorical_color(self, value: float) -> str:
        """Get categorical color by index."""
        index = int(value) % len(self.colors)
        return self.colors[index]

    def _threshold_color(self, value: float) -> str:
        """Get color based on thresholds."""
        if not self.thresholds:
            return self._linear_interpolate(value)

        for i, threshold in enumerate(self.thresholds):
            if value < threshold:
                return self.colors[i] if i < len(self.colors) else self.colors[-1]

        return self.colors[-1]

    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """Convert hex to RGB."""
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def to_dict(self) -> dict:
        return {
            "scale_type": self.scale_type.value,
            "colors": self.colors,
            "domain": list(self.domain),
            "thresholds": self.thresholds,
        }


@dataclass
class IconMapping:
    """
    Maps state values to icons.
    """
    icon_set: str  # Name of icon set (e.g., "lucide", "heroicons")
    mappings: Dict[str, str]  # value -> icon name
    default_icon: str

    def get_icon(self, value: str) -> str:
        """Get icon for a value."""
        return self.mappings.get(value, self.default_icon)

    def to_dict(self) -> dict:
        return {
            "icon_set": self.icon_set,
            "mappings": self.mappings,
            "default_icon": self.default_icon,
        }


@dataclass
class AnimationConfig:
    """
    Configuration for an animation effect.
    """
    animation_type: AnimationType
    duration_ms: int = 500
    easing: str = "ease-in-out"  # CSS easing function
    repeat: bool = False
    intensity: float = 1.0  # 0-1, scales effect magnitude
    trigger_on: List[str] = field(default_factory=list)  # Events that trigger

    def to_dict(self) -> dict:
        return {
            "type": self.animation_type.value,
            "duration_ms": self.duration_ms,
            "easing": self.easing,
            "repeat": self.repeat,
            "intensity": self.intensity,
            "trigger_on": self.trigger_on,
        }


@dataclass
class PropertyMapping:
    """
    Maps a state property to a visual property.
    """
    state_property: str  # e.g., "stance", "emotion", "influence"
    visual_property: str  # e.g., "fill_color", "border_color", "size"
    color_scale: Optional[ColorScale] = None
    value_range: Tuple[float, float] = (0.0, 1.0)
    output_range: Tuple[float, float] = (0.0, 1.0)
    transform: str = "linear"  # "linear", "log", "sqrt", "exp"

    def map_value(self, value: float) -> Any:
        """Map state value to visual value."""
        # Normalize input
        min_in, max_in = self.value_range
        if max_in == min_in:
            normalized = 0.5
        else:
            normalized = (value - min_in) / (max_in - min_in)
        normalized = max(0, min(1, normalized))

        # Apply transform
        if self.transform == "log":
            normalized = self._log_transform(normalized)
        elif self.transform == "sqrt":
            normalized = normalized ** 0.5
        elif self.transform == "exp":
            normalized = normalized ** 2

        # Map to output range
        min_out, max_out = self.output_range
        output = min_out + normalized * (max_out - min_out)

        # If color scale, get color
        if self.color_scale:
            return self.color_scale.get_color(normalized)

        return output

    def _log_transform(self, value: float) -> float:
        """Apply logarithmic transform."""
        import math
        if value <= 0:
            return 0
        return math.log10(value * 9 + 1) / math.log10(10)

    def to_dict(self) -> dict:
        return {
            "state_property": self.state_property,
            "visual_property": self.visual_property,
            "color_scale": self.color_scale.to_dict() if self.color_scale else None,
            "value_range": list(self.value_range),
            "output_range": list(self.output_range),
            "transform": self.transform,
        }


@dataclass
class RenderingProfile:
    """
    Complete rendering profile for a domain template.
    Maps all state properties to visual properties.
    """
    profile_id: str
    name: str
    domain_template: str
    property_mappings: List[PropertyMapping]
    icon_mappings: Dict[str, IconMapping]  # property -> IconMapping
    animations: Dict[str, AnimationConfig]  # event -> AnimationConfig
    default_fill: str = "#00ffff"
    default_border: str = "#ffffff"
    default_opacity: float = 0.8
    hover_scale: float = 1.2

    def get_visual_properties(
        self,
        agent_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Get all visual properties for an agent state."""
        result = {
            "fill_color": self.default_fill,
            "border_color": self.default_border,
            "opacity": self.default_opacity,
        }

        for mapping in self.property_mappings:
            if mapping.state_property in agent_state:
                value = agent_state[mapping.state_property]
                if isinstance(value, (int, float)):
                    result[mapping.visual_property] = mapping.map_value(value)

        return result

    def get_animation(self, event_type: str) -> Optional[AnimationConfig]:
        """Get animation config for an event."""
        return self.animations.get(event_type)

    def get_icon(
        self,
        property_name: str,
        value: str,
    ) -> Optional[str]:
        """Get icon for a property value."""
        if property_name in self.icon_mappings:
            return self.icon_mappings[property_name].get_icon(value)
        return None

    def to_dict(self) -> dict:
        return {
            "profile_id": self.profile_id,
            "name": self.name,
            "domain_template": self.domain_template,
            "property_mappings": [m.to_dict() for m in self.property_mappings],
            "icon_mappings": {k: v.to_dict() for k, v in self.icon_mappings.items()},
            "animations": {k: v.to_dict() for k, v in self.animations.items()},
            "default_fill": self.default_fill,
            "default_border": self.default_border,
            "default_opacity": self.default_opacity,
            "hover_scale": self.hover_scale,
        }


# ============================================================
# Default Rendering Profiles per Domain Template
# ============================================================

# Common color scales
STANCE_COLORS = ColorScale(
    scale_type=ColorScaleType.DIVERGING,
    colors=["#ff4444", "#888888", "#44ff44"],  # negative-neutral-positive
    domain=(-1.0, 1.0),
)

EMOTION_COLORS = ColorScale(
    scale_type=ColorScaleType.LINEAR,
    colors=["#1a1a2e", "#00ffff", "#ff00ff"],  # calm-engaged-intense
    domain=(0.0, 1.0),
)

INFLUENCE_COLORS = ColorScale(
    scale_type=ColorScaleType.LINEAR,
    colors=["#333333", "#00ffff", "#ffffff"],  # low-medium-high
    domain=(0.0, 1.0),
)

EXPOSURE_COLORS = ColorScale(
    scale_type=ColorScaleType.LINEAR,
    colors=["#0a0a0f", "#ff8800", "#ffff00"],  # unexposed-partial-full
    domain=(0.0, 1.0),
)


# Common animations
PULSE_ANIMATION = AnimationConfig(
    animation_type=AnimationType.PULSE,
    duration_ms=300,
    intensity=0.3,
    trigger_on=["action_taken", "decision_made"],
)

GLOW_ANIMATION = AnimationConfig(
    animation_type=AnimationType.GLOW,
    duration_ms=500,
    intensity=0.5,
    trigger_on=["event_received", "influence_change"],
)

RIPPLE_ANIMATION = AnimationConfig(
    animation_type=AnimationType.RIPPLE,
    duration_ms=800,
    intensity=1.0,
    trigger_on=["major_event", "conversion"],
)


DEFAULT_RENDERING_PROFILES: Dict[str, RenderingProfile] = {
    "consumer": RenderingProfile(
        profile_id="consumer-rendering",
        name="Consumer Behavior Rendering",
        domain_template="consumer",
        property_mappings=[
            PropertyMapping(
                state_property="stance",
                visual_property="fill_color",
                color_scale=STANCE_COLORS,
                value_range=(-1.0, 1.0),
            ),
            PropertyMapping(
                state_property="emotion",
                visual_property="border_color",
                color_scale=EMOTION_COLORS,
            ),
            PropertyMapping(
                state_property="influence",
                visual_property="size",
                value_range=(0.0, 1.0),
                output_range=(6.0, 16.0),
            ),
            PropertyMapping(
                state_property="exposure",
                visual_property="opacity",
                value_range=(0.0, 1.0),
                output_range=(0.4, 1.0),
            ),
        ],
        icon_mappings={
            "last_action": IconMapping(
                icon_set="lucide",
                mappings={
                    "purchase": "shopping-cart",
                    "browse": "eye",
                    "share": "share-2",
                    "review": "message-square",
                    "abandon": "x",
                    "save": "heart",
                },
                default_icon="circle",
            ),
            "segment": IconMapping(
                icon_set="lucide",
                mappings={
                    "early_adopter": "zap",
                    "innovator": "lightbulb",
                    "mainstream": "users",
                    "laggard": "clock",
                    "influencer": "star",
                },
                default_icon="user",
            ),
        },
        animations={
            "purchase": RIPPLE_ANIMATION,
            "conversion": RIPPLE_ANIMATION,
            "action_taken": PULSE_ANIMATION,
            "influence_change": GLOW_ANIMATION,
        },
        default_fill="#00ffff",
        default_border="#ffffff",
    ),

    "financial": RenderingProfile(
        profile_id="financial-rendering",
        name="Financial Decision Rendering",
        domain_template="financial",
        property_mappings=[
            PropertyMapping(
                state_property="stance",  # risk attitude
                visual_property="fill_color",
                color_scale=ColorScale(
                    scale_type=ColorScaleType.DIVERGING,
                    colors=["#4444ff", "#888888", "#ff4444"],  # conservative-neutral-aggressive
                    domain=(-1.0, 1.0),
                ),
                value_range=(-1.0, 1.0),
            ),
            PropertyMapping(
                state_property="exposure",  # market exposure
                visual_property="border_color",
                color_scale=EXPOSURE_COLORS,
            ),
            PropertyMapping(
                state_property="influence",
                visual_property="size",
                output_range=(8.0, 20.0),
            ),
        ],
        icon_mappings={
            "last_action": IconMapping(
                icon_set="lucide",
                mappings={
                    "buy": "trending-up",
                    "sell": "trending-down",
                    "hold": "pause",
                    "diversify": "pie-chart",
                    "research": "search",
                },
                default_icon="circle",
            ),
        },
        animations={
            "trade_executed": RIPPLE_ANIMATION,
            "market_event": GLOW_ANIMATION,
            "decision_made": PULSE_ANIMATION,
        },
        default_fill="#00ff88",
        default_border="#ffffff",
    ),

    "career": RenderingProfile(
        profile_id="career-rendering",
        name="Career Path Rendering",
        domain_template="career",
        property_mappings=[
            PropertyMapping(
                state_property="stance",  # job satisfaction
                visual_property="fill_color",
                color_scale=ColorScale(
                    scale_type=ColorScaleType.DIVERGING,
                    colors=["#ff4444", "#ffff44", "#44ff44"],  # unhappy-neutral-satisfied
                    domain=(-1.0, 1.0),
                ),
                value_range=(-1.0, 1.0),
            ),
            PropertyMapping(
                state_property="influence",  # career level
                visual_property="size",
                output_range=(8.0, 18.0),
            ),
            PropertyMapping(
                state_property="emotion",  # motivation
                visual_property="border_color",
                color_scale=EMOTION_COLORS,
            ),
        ],
        icon_mappings={
            "last_action": IconMapping(
                icon_set="lucide",
                mappings={
                    "apply": "send",
                    "interview": "mic",
                    "negotiate": "message-square",
                    "accept": "check",
                    "reject": "x",
                    "promote": "arrow-up",
                    "resign": "log-out",
                },
                default_icon="briefcase",
            ),
        },
        animations={
            "promotion": RIPPLE_ANIMATION,
            "job_change": GLOW_ANIMATION,
            "application": PULSE_ANIMATION,
        },
        default_fill="#ff8800",
        default_border="#ffffff",
    ),

    "default": RenderingProfile(
        profile_id="default-rendering",
        name="Default Rendering",
        domain_template="default",
        property_mappings=[
            PropertyMapping(
                state_property="stance",
                visual_property="fill_color",
                color_scale=STANCE_COLORS,
                value_range=(-1.0, 1.0),
            ),
            PropertyMapping(
                state_property="emotion",
                visual_property="border_color",
                color_scale=EMOTION_COLORS,
            ),
            PropertyMapping(
                state_property="influence",
                visual_property="size",
                output_range=(6.0, 14.0),
            ),
        ],
        icon_mappings={},
        animations={
            "action_taken": PULSE_ANIMATION,
            "event_received": GLOW_ANIMATION,
        },
        default_fill="#00ffff",
        default_border="#ffffff",
    ),
}


@dataclass
class RenderedAgent:
    """
    An agent with computed visual properties.
    Ready for frontend rendering.
    """
    agent_id: str
    x: float
    y: float
    size: float
    fill_color: str
    border_color: str
    opacity: float
    icon: Optional[str] = None
    animation: Optional[str] = None
    tooltip: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "x": self.x,
            "y": self.y,
            "size": self.size,
            "fill_color": self.fill_color,
            "border_color": self.border_color,
            "opacity": self.opacity,
            "icon": self.icon,
            "animation": self.animation,
            "tooltip": self.tooltip,
        }


class RenderingService:
    """
    Service for rendering mappings.
    Combines layout and rendering profiles to produce render-ready agents.
    """

    def __init__(self):
        self.profiles: Dict[str, RenderingProfile] = dict(DEFAULT_RENDERING_PROFILES)

    def get_profile(self, domain_template: str) -> RenderingProfile:
        """Get rendering profile for a domain template."""
        return self.profiles.get(domain_template, self.profiles["default"])

    def render_agent(
        self,
        agent_state: Dict[str, Any],
        position: Dict[str, float],
        domain_template: str = "default",
        active_event: Optional[str] = None,
    ) -> RenderedAgent:
        """
        Render an agent with full visual properties.

        Args:
            agent_state: Agent state dictionary
            position: Position from layout calculator
            domain_template: Domain for rendering profile
            active_event: Currently active event (for animation)

        Returns:
            RenderedAgent ready for frontend
        """
        profile = self.get_profile(domain_template)
        visual = profile.get_visual_properties(agent_state)

        # Get icon for last action
        icon = None
        if "last_action" in agent_state:
            icon = profile.get_icon("last_action", agent_state["last_action"])

        # Get animation for active event
        animation = None
        if active_event:
            anim_config = profile.get_animation(active_event)
            if anim_config:
                animation = anim_config.animation_type.value

        # Build tooltip
        tooltip_parts = [f"Agent: {agent_state.get('agent_id', 'Unknown')}"]
        if "segment" in agent_state:
            tooltip_parts.append(f"Segment: {agent_state['segment']}")
        if "stance" in agent_state:
            tooltip_parts.append(f"Stance: {agent_state['stance']:.2f}")
        tooltip = " | ".join(tooltip_parts)

        return RenderedAgent(
            agent_id=agent_state.get("agent_id", agent_state.get("id", "")),
            x=position.get("x", 0),
            y=position.get("y", 0),
            size=visual.get("size", profile.default_opacity),
            fill_color=visual.get("fill_color", profile.default_fill),
            border_color=visual.get("border_color", profile.default_border),
            opacity=visual.get("opacity", profile.default_opacity),
            icon=icon,
            animation=animation,
            tooltip=tooltip,
        )

    def render_frame(
        self,
        agents: List[Dict[str, Any]],
        positions: List[Dict[str, Any]],
        domain_template: str = "default",
        events: Optional[List[str]] = None,
    ) -> List[RenderedAgent]:
        """
        Render a complete frame of agents.

        Args:
            agents: List of agent states
            positions: List of positions from layout calculator
            domain_template: Domain for rendering profile
            events: Events active at this frame

        Returns:
            List of RenderedAgent objects
        """
        # Build position lookup
        pos_by_id = {p.get("agent_id", p.get("id")): p for p in positions}

        rendered = []
        for agent in agents:
            agent_id = agent.get("agent_id", agent.get("id"))
            pos = pos_by_id.get(agent_id, {"x": 0, "y": 0})

            # Check if agent is affected by any event
            active_event = None
            if events and agent.get("last_event") in events:
                active_event = agent.get("last_event")

            rendered.append(self.render_agent(
                agent_state=agent,
                position=pos,
                domain_template=domain_template,
                active_event=active_event,
            ))

        return rendered


# Singleton instance
_rendering_service: Optional[RenderingService] = None


def get_rendering_service() -> RenderingService:
    """Get the rendering service instance."""
    global _rendering_service
    if _rendering_service is None:
        _rendering_service = RenderingService()
    return _rendering_service
