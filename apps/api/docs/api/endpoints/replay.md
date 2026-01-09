# 2D Replay API (Read-Only)

**Tag:** `2D Replay`
**Base Path:** `/api/v1/replay`

The 2D Replay API provides visualization-optimized data for replaying simulations. This API is **strictly read-only** and implements constraint **C3: Replay is Read-Only** - replay never triggers simulations.

---

## Core Concepts

### Read-Only Guarantee (C3)

All replay endpoints are **strictly read-only**:
- No mutations to simulation state
- No triggering of new runs
- Data is pre-computed and cached
- Safe for repeated playback

### Replay vs Telemetry

| Aspect | Telemetry API | Replay API |
|--------|---------------|------------|
| Purpose | Data analysis | Visualization |
| Format | Raw metrics | Render-ready |
| Granularity | Full precision | Downsampled |
| Response size | Larger | Optimized |

### Visualization Components

Replay data is structured for 2D canvas rendering:
- **Zones**: Semantic regions (Supporters, Neutral, Skeptics)
- **Agents**: Positioned sprites with visual attributes
- **Layers**: Toggleable visual dimensions (stance, emotion, influence)
- **Events**: Triggered interventions with visual markers

---

## Data Model

### ReplayTimeline

```json
{
  "session_id": "uuid",
  "node_id": "uuid",
  "total_ticks": 100,
  "keyframe_interval": 5,
  "keyframe_ticks": [0, 5, 10, 15, 20, ...],
  "zone_definitions": [
    {
      "id": "supporters",
      "name": "Supporters",
      "bounds": {"x": 0, "y": 0, "width": 300, "height": 600},
      "color": "#10b981"
    },
    {
      "id": "neutral",
      "name": "Neutral",
      "bounds": {"x": 300, "y": 0, "width": 400, "height": 600},
      "color": "#6b7280"
    },
    {
      "id": "skeptics",
      "name": "Skeptics",
      "bounds": {"x": 700, "y": 0, "width": 300, "height": 600},
      "color": "#ef4444"
    }
  ],
  "layer_definitions": [
    {"id": "stance", "name": "Stance", "default_visible": true},
    {"id": "emotion", "name": "Emotion", "default_visible": false},
    {"id": "influence", "name": "Influence Network", "default_visible": false}
  ],
  "event_markers": [
    {"tick": 15, "type": "media_event", "name": "News Coverage"},
    {"tick": 40, "type": "price_change", "name": "Price Drop"}
  ]
}
```

### ReplayWorldState

```json
{
  "tick": 50,
  "global_metrics": {
    "adoption_rate": 0.65,
    "avg_sentiment": 0.55,
    "active_agents": 9500
  },
  "zone_populations": {
    "supporters": 4500,
    "neutral": 3500,
    "skeptics": 1500
  },
  "agents": [
    {
      "id": "agent-1",
      "position": {"x": 150, "y": 200},
      "zone": "supporters",
      "stance": 0.8,
      "emotion": 0.6,
      "influence_score": 0.7,
      "segment": "early_adopter",
      "recent_action": "adopted"
    }
  ],
  "active_events": [
    {
      "id": "event-1",
      "type": "media_event",
      "intensity": 0.8,
      "affected_zone": "neutral"
    }
  ]
}
```

### ReplayChunk

```json
{
  "start_tick": 0,
  "end_tick": 10,
  "states": [
    {"tick": 0, "agents": [...], "metrics": {...}},
    {"tick": 1, "agents": [...], "metrics": {...}},
    {"tick": 2, "agents": [...], "metrics": {...}}
  ],
  "transitions": [
    {
      "tick": 5,
      "agent_id": "agent-123",
      "from_zone": "neutral",
      "to_zone": "supporters",
      "reason": "peer_influence"
    }
  ]
}
```

---

## Endpoints

### Load Replay

```http
POST /api/v1/replay/load
Content-Type: application/json
```

Initialize a replay session for a node.

**Request Body:**

```json
{
  "node_id": "uuid",
  "layout_profile": "default",
  "downsampling": {
    "max_agents": 1000,
    "sampling_strategy": "representative"
  },
  "preload_ticks": 20
}
```

**Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `node_id` | uuid | - | Node to replay |
| `layout_profile` | string | "default" | Zone layout profile |
| `max_agents` | int | 1000 | Max agents to render |
| `sampling_strategy` | string | "representative" | How to sample agents |
| `preload_ticks` | int | 10 | Ticks to preload |

**Response:**

```json
{
  "session_id": "uuid",
  "node_id": "uuid",
  "timeline": {
    "total_ticks": 100,
    "keyframe_interval": 5,
    "keyframe_ticks": [0, 5, 10, ...]
  },
  "zones": [
    {
      "id": "supporters",
      "name": "Supporters",
      "bounds": {"x": 0, "y": 0, "width": 300, "height": 600}
    }
  ],
  "layers": [
    {"id": "stance", "name": "Stance", "default_visible": true}
  ],
  "initial_state": {
    "tick": 0,
    "agents": [...],
    "metrics": {...}
  },
  "event_markers": [
    {"tick": 15, "type": "media_event"}
  ]
}
```

---

### Get State at Tick

```http
GET /api/v1/replay/{session_id}/state
```

Get world state at a specific tick.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `tick` | int | 0 | Target tick |
| `include_agents` | bool | true | Include agent data |
| `layers` | string | "all" | Comma-separated layer IDs |

**Response:**

```json
{
  "tick": 50,
  "is_keyframe": true,
  "global_metrics": {
    "adoption_rate": 0.65,
    "avg_sentiment": 0.55
  },
  "zone_populations": {
    "supporters": 450,
    "neutral": 350,
    "skeptics": 200
  },
  "agents": [
    {
      "id": "agent-1",
      "position": {"x": 150, "y": 200},
      "zone": "supporters",
      "stance": 0.8,
      "emotion": 0.6,
      "influence_score": 0.7
    }
  ],
  "active_events": []
}
```

---

### Get Chunk

```http
GET /api/v1/replay/{session_id}/chunk
```

Get a chunk of consecutive ticks for smooth playback.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `start_tick` | int | 0 | Start of chunk |
| `end_tick` | int | - | End of chunk |
| `include_transitions` | bool | true | Include zone transitions |

**Response:**

```json
{
  "start_tick": 0,
  "end_tick": 10,
  "chunk_size": 11,
  "states": [
    {
      "tick": 0,
      "zone_populations": {"supporters": 400, "neutral": 400, "skeptics": 200},
      "agents": [...]
    },
    {
      "tick": 1,
      "zone_populations": {"supporters": 402, "neutral": 398, "skeptics": 200},
      "agents": [...]
    }
  ],
  "transitions": [
    {
      "tick": 3,
      "agent_id": "agent-123",
      "from_zone": "neutral",
      "to_zone": "supporters",
      "from_position": {"x": 350, "y": 300},
      "to_position": {"x": 150, "y": 280}
    }
  ],
  "events_in_range": [
    {
      "tick": 5,
      "id": "event-1",
      "type": "media_event",
      "intensity": 1.0
    }
  ]
}
```

---

### Seek to Tick

```http
POST /api/v1/replay/{session_id}/seek
Content-Type: application/json
```

Seek to a specific tick and get state.

**Request Body:**

```json
{
  "tick": 50,
  "preload_range": 10
}
```

**Response:**

```json
{
  "tick": 50,
  "state": {
    "zone_populations": {...},
    "agents": [...],
    "active_events": [...]
  },
  "preloaded_range": {
    "start": 45,
    "end": 55
  },
  "nearest_keyframe": 50
}
```

---

### Get Agent Focus

```http
GET /api/v1/replay/{session_id}/agent/{agent_id}
```

Get detailed trajectory for a specific agent (for inspector panel).

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `include_reasoning` | bool | false | Include decision reasoning |

**Response:**

```json
{
  "agent_id": "agent-123",
  "persona_name": "Urban Professional #456",
  "segment": "early_adopter",
  "current_state": {
    "tick": 50,
    "zone": "supporters",
    "position": {"x": 150, "y": 200},
    "stance": 0.85,
    "emotion": 0.7
  },
  "trajectory_summary": {
    "zones_visited": ["skeptics", "neutral", "supporters"],
    "total_transitions": 3,
    "final_decision": "adopted",
    "decision_tick": 45
  },
  "key_moments": [
    {
      "tick": 15,
      "event": "Media exposure shifted perception",
      "state_change": {"stance": 0.3, "to_stance": 0.5}
    },
    {
      "tick": 30,
      "event": "Peer recommendation received",
      "state_change": {"stance": 0.6, "to_stance": 0.75}
    }
  ],
  "influence_connections": [
    {"agent_id": "agent-789", "strength": 0.8, "direction": "incoming"},
    {"agent_id": "agent-234", "strength": 0.5, "direction": "outgoing"}
  ]
}
```

---

### Stream Replay (SSE)

```http
GET /api/v1/replay/{session_id}/stream
Accept: text/event-stream
```

Stream replay data for real-time playback.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `start_tick` | int | 0 | Start streaming from |
| `speed` | float | 1.0 | Playback speed multiplier |

**Events:**

```
event: state
data: {"tick": 0, "zone_populations": {...}, "agents": [...]}

event: state
data: {"tick": 1, "zone_populations": {...}, "agents": [...]}

event: transition
data: {"tick": 3, "agent_id": "agent-123", "from": "neutral", "to": "supporters"}

event: event
data: {"tick": 5, "type": "media_event", "name": "News Coverage", "intensity": 1.0}

event: end
data: {"final_tick": 100, "session_id": "uuid"}
```

---

### Close Replay Session

```http
DELETE /api/v1/replay/{session_id}
```

Close a replay session and release resources.

**Response:** `204 No Content`

---

## Layout Profiles

### Default Layout

```json
{
  "id": "default",
  "name": "Standard Three-Zone",
  "canvas_size": {"width": 1000, "height": 600},
  "zones": [
    {"id": "supporters", "x": 0, "y": 0, "width": 300, "height": 600},
    {"id": "neutral", "x": 300, "y": 0, "width": 400, "height": 600},
    {"id": "skeptics", "x": 700, "y": 0, "width": 300, "height": 600}
  ]
}
```

### Quadrant Layout

```json
{
  "id": "quadrant",
  "name": "Four-Quadrant",
  "canvas_size": {"width": 800, "height": 800},
  "zones": [
    {"id": "high_aware_positive", "x": 400, "y": 0, "width": 400, "height": 400},
    {"id": "low_aware_positive", "x": 0, "y": 0, "width": 400, "height": 400},
    {"id": "low_aware_negative", "x": 0, "y": 400, "width": 400, "height": 400},
    {"id": "high_aware_negative", "x": 400, "y": 400, "width": 400, "height": 400}
  ]
}
```

---

## Error Responses

### 404 Not Found - Session Expired

```json
{
  "detail": "Replay session not found or expired",
  "status_code": 404,
  "error_code": "SESSION_NOT_FOUND",
  "hint": "Replay sessions expire after 30 minutes of inactivity"
}
```

### 400 Bad Request - Invalid Tick

```json
{
  "detail": "Tick 150 is out of range",
  "status_code": 400,
  "error_code": "INVALID_TICK",
  "valid_range": {"min": 0, "max": 100}
}
```

### 404 Not Found - No Telemetry

```json
{
  "detail": "Node has no telemetry data for replay",
  "status_code": 404,
  "error_code": "NO_TELEMETRY",
  "node_status": "pending",
  "hint": "Wait for the simulation run to complete"
}
```

---

## Caching

Replay responses are cached aggressively:

| Endpoint | Cache TTL | Notes |
|----------|-----------|-------|
| Load | 1 hour | Session initialization |
| State | 24 hours | Immutable per tick |
| Chunk | 24 hours | Immutable data |
| Agent | 24 hours | Immutable trajectory |

---

## Examples

### Basic Replay Playback

```python
import httpx
import time

client = httpx.Client(
    base_url="https://api.agentverse.ai/api/v1",
    headers={"Authorization": f"Bearer {token}"}
)

# Load replay
session = client.post("/replay/load", json={
    "node_id": "node-uuid",
    "max_agents": 500
}).json()

session_id = session['session_id']
total_ticks = session['timeline']['total_ticks']

# Play through ticks
for tick in range(0, total_ticks, 5):
    state = client.get(
        f"/replay/{session_id}/state",
        params={"tick": tick}
    ).json()

    print(f"Tick {tick}: Supporters={state['zone_populations']['supporters']}")
    time.sleep(0.5)

# Cleanup
client.delete(f"/replay/{session_id}")
```

### Streaming Playback

```python
import httpx
import sseclient

with httpx.stream(
    "GET",
    f"/replay/{session_id}/stream",
    params={"speed": 2.0},
    headers={
        "Accept": "text/event-stream",
        "Authorization": f"Bearer {token}"
    }
) as response:
    sse = sseclient.SSEClient(response.iter_bytes())
    for event in sse.events():
        if event.event == "state":
            state = json.loads(event.data)
            render_frame(state)
        elif event.event == "transition":
            transition = json.loads(event.data)
            animate_transition(transition)
        elif event.event == "end":
            break
```

### Agent Inspection

```python
# Get agent details when clicked
agent_data = client.get(
    f"/replay/{session_id}/agent/{agent_id}",
    params={"include_reasoning": True}
).json()

print(f"Agent: {agent_data['persona_name']}")
print(f"Current zone: {agent_data['current_state']['zone']}")
print(f"Decision: {agent_data['trajectory_summary']['final_decision']}")

for moment in agent_data['key_moments']:
    print(f"  Tick {moment['tick']}: {moment['event']}")
```
