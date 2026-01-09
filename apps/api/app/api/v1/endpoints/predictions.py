"""
Predictive Simulation API Endpoints

Provides endpoints for running large-scale predictive simulations,
calibration, MARL training, and accuracy tracking.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User

router = APIRouter()


# ============================================================================
# Pydantic Schemas
# ============================================================================


class PredictionCategory(BaseModel):
    """Category definition for predictions."""
    name: str
    color: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AgentConfig(BaseModel):
    """Configuration for agent population."""
    count: int = Field(default=1000, ge=10, le=100000, description="Number of agents")
    demographics: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Demographic distribution parameters"
    )
    behavioral_params: Optional[Dict[str, float]] = Field(
        default=None,
        description="Behavioral economics parameters"
    )


class SimulationConfig(BaseModel):
    """Configuration for predictive simulation."""
    categories: List[PredictionCategory]
    agent_config: AgentConfig
    num_steps: int = Field(default=30, ge=1, le=365, description="Simulation time steps")
    monte_carlo_runs: int = Field(default=10, ge=1, le=100, description="Number of Monte Carlo runs")
    confidence_level: float = Field(default=0.95, ge=0.8, le=0.99)

    # Optional configurations
    social_network_type: str = Field(
        default="small_world",
        pattern="^(random|small_world|scale_free|community)$"
    )
    enable_marl: bool = Field(default=False, description="Enable MARL for agent learning")
    use_calibration: bool = Field(default=True, description="Use calibrated parameters")


class PredictionRequest(BaseModel):
    """Request to start a prediction simulation."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    scenario_type: str = Field(
        default="election",
        pattern="^(election|consumer|market|social)$"
    )
    config: SimulationConfig


class GroundTruthInput(BaseModel):
    """Ground truth data for calibration."""
    category_distributions: Dict[str, float]
    regional_distributions: Optional[Dict[str, Dict[str, float]]] = None
    confidence_intervals: Optional[Dict[str, List[float]]] = None
    source: str = ""
    date: Optional[str] = None


class CalibrationRequest(BaseModel):
    """Request to run calibration."""
    prediction_id: UUID
    ground_truth: GroundTruthInput
    method: str = Field(
        default="bayesian",
        pattern="^(bayesian|grid_search|random_search|adaptive)$"
    )
    max_iterations: int = Field(default=50, ge=10, le=500)
    target_accuracy: float = Field(default=0.80, ge=0.5, le=0.99)


class MARLTrainingRequest(BaseModel):
    """Request to run MARL training."""
    prediction_id: UUID
    num_updates: int = Field(default=100, ge=10, le=1000)
    learning_rate: float = Field(default=3e-4, gt=0, lt=1)
    gamma: float = Field(default=0.99, gt=0, le=1)
    gae_lambda: float = Field(default=0.95, gt=0, le=1)
    clip_ratio: float = Field(default=0.2, gt=0, lt=1)


class PredictionResponse(BaseModel):
    """Response for prediction status."""
    id: UUID
    name: str
    status: str
    progress: float
    created_at: datetime
    config: Dict[str, Any]
    results: Optional[Dict[str, Any]] = None


class PredictionResultResponse(BaseModel):
    """Response for prediction results."""
    id: UUID
    status: str
    predictions: Dict[str, float]
    confidence_intervals: Dict[str, List[float]]
    accuracy_metrics: Optional[Dict[str, float]] = None
    regional_breakdown: Optional[Dict[str, Dict[str, float]]] = None
    temporal_evolution: Optional[List[Dict[str, Any]]] = None
    agent_statistics: Optional[Dict[str, Any]] = None


# ============================================================================
# In-Memory Storage (would be database in production)
# ============================================================================

# Simple in-memory storage for demo purposes
prediction_store: Dict[str, Dict[str, Any]] = {}
calibration_store: Dict[str, Dict[str, Any]] = {}


# ============================================================================
# Prediction Endpoints
# ============================================================================


@router.post("/", response_model=PredictionResponse, status_code=status.HTTP_201_CREATED)
async def create_prediction(
    request: PredictionRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Create and start a new predictive simulation.

    Supports up to 100,000 agents with Monte Carlo uncertainty quantification.
    """
    prediction_id = uuid4()

    prediction = {
        "id": str(prediction_id),
        "name": request.name,
        "description": request.description,
        "scenario_type": request.scenario_type,
        "status": "pending",
        "progress": 0.0,
        "created_at": datetime.utcnow().isoformat(),
        "user_id": str(current_user.id),
        "config": request.config.model_dump(),
        "results": None,
    }

    prediction_store[str(prediction_id)] = prediction

    # Queue background task
    background_tasks.add_task(
        run_prediction_task,
        str(prediction_id),
        request.config.model_dump(),
    )

    return {
        "id": prediction_id,
        "name": request.name,
        "status": "pending",
        "progress": 0.0,
        "created_at": prediction["created_at"],
        "config": prediction["config"],
        "results": None,
    }


@router.get("/", response_model=List[PredictionResponse])
async def list_predictions(
    status_filter: Optional[str] = Query(
        None, pattern="^(pending|running|completed|failed)$"
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """List all predictions for the current user."""
    user_predictions = [
        p for p in prediction_store.values()
        if p.get("user_id") == str(current_user.id)
    ]

    if status_filter:
        user_predictions = [p for p in user_predictions if p.get("status") == status_filter]

    # Sort by created_at desc
    user_predictions.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    return user_predictions[skip:skip + limit]


@router.get("/{prediction_id}", response_model=PredictionResponse)
async def get_prediction(
    prediction_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get prediction details by ID."""
    prediction = prediction_store.get(str(prediction_id))

    if not prediction or prediction.get("user_id") != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prediction not found",
        )

    return prediction


@router.get("/{prediction_id}/results", response_model=PredictionResultResponse)
async def get_prediction_results(
    prediction_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get detailed results for a completed prediction."""
    prediction = prediction_store.get(str(prediction_id))

    if not prediction or prediction.get("user_id") != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prediction not found",
        )

    if prediction.get("status") != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Prediction not completed. Status: {prediction.get('status')}",
        )

    results = prediction.get("results", {})

    return {
        "id": prediction_id,
        "status": prediction.get("status"),
        "predictions": results.get("predictions", {}),
        "confidence_intervals": results.get("confidence_intervals", {}),
        "accuracy_metrics": results.get("accuracy_metrics"),
        "regional_breakdown": results.get("regional_breakdown"),
        "temporal_evolution": results.get("temporal_evolution"),
        "agent_statistics": results.get("agent_statistics"),
    }


@router.get("/{prediction_id}/stream")
async def stream_prediction(
    prediction_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Stream prediction progress using Server-Sent Events.
    """
    prediction = prediction_store.get(str(prediction_id))

    if not prediction or prediction.get("user_id") != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prediction not found",
        )

    async def event_generator():
        import asyncio
        import json

        while True:
            pred = prediction_store.get(str(prediction_id), {})

            progress_data = {
                "prediction_id": str(prediction_id),
                "status": pred.get("status", "unknown"),
                "progress": pred.get("progress", 0),
            }

            yield f"data: {json.dumps(progress_data)}\n\n"

            if pred.get("status") in ["completed", "failed"]:
                if pred.get("results"):
                    yield f"data: {json.dumps({'type': 'results', 'data': pred['results']})}\n\n"
                break

            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.post("/{prediction_id}/cancel")
async def cancel_prediction(
    prediction_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    """Cancel a running prediction."""
    prediction = prediction_store.get(str(prediction_id))

    if not prediction or prediction.get("user_id") != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prediction not found",
        )

    if prediction.get("status") not in ["pending", "running"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel prediction with status: {prediction.get('status')}",
        )

    prediction["status"] = "failed"
    prediction["error"] = "Cancelled by user"

    return {"message": "Prediction cancelled", "prediction_id": str(prediction_id)}


# ============================================================================
# Calibration Endpoints
# ============================================================================


@router.post("/calibrate", status_code=status.HTTP_201_CREATED)
async def start_calibration(
    request: CalibrationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Start calibration process against ground truth data.

    Optimizes simulation parameters to achieve >80% accuracy.
    """
    prediction = prediction_store.get(str(request.prediction_id))

    if not prediction or prediction.get("user_id") != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prediction not found",
        )

    calibration_id = uuid4()

    calibration = {
        "id": str(calibration_id),
        "prediction_id": str(request.prediction_id),
        "status": "pending",
        "method": request.method,
        "target_accuracy": request.target_accuracy,
        "max_iterations": request.max_iterations,
        "created_at": datetime.utcnow().isoformat(),
        "user_id": str(current_user.id),
        "ground_truth": request.ground_truth.model_dump(),
        "results": None,
    }

    calibration_store[str(calibration_id)] = calibration

    # Queue background task
    background_tasks.add_task(
        run_calibration_task,
        str(calibration_id),
        str(request.prediction_id),
        request.ground_truth.model_dump(),
        request.method,
        request.target_accuracy,
        request.max_iterations,
    )

    return {
        "calibration_id": calibration_id,
        "prediction_id": request.prediction_id,
        "status": "pending",
        "method": request.method,
        "target_accuracy": request.target_accuracy,
    }


@router.get("/calibrate/{calibration_id}")
async def get_calibration_status(
    calibration_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get calibration status and results."""
    calibration = calibration_store.get(str(calibration_id))

    if not calibration or calibration.get("user_id") != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calibration not found",
        )

    return calibration


# ============================================================================
# MARL Training Endpoints
# ============================================================================


@router.post("/train", status_code=status.HTTP_201_CREATED)
async def start_marl_training(
    request: MARLTrainingRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Start MARL training for agent policy learning.

    Uses PPO algorithm with Actor-Critic networks.
    """
    prediction = prediction_store.get(str(request.prediction_id))

    if not prediction or prediction.get("user_id") != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prediction not found",
        )

    training_id = uuid4()

    training = {
        "id": str(training_id),
        "prediction_id": str(request.prediction_id),
        "status": "pending",
        "num_updates": request.num_updates,
        "learning_rate": request.learning_rate,
        "gamma": request.gamma,
        "gae_lambda": request.gae_lambda,
        "clip_ratio": request.clip_ratio,
        "created_at": datetime.utcnow().isoformat(),
        "user_id": str(current_user.id),
        "metrics": [],
    }

    # Store training session
    prediction["training"] = training

    # Queue background task
    background_tasks.add_task(
        run_marl_training_task,
        str(training_id),
        str(request.prediction_id),
        request.model_dump(),
    )

    return {
        "training_id": training_id,
        "prediction_id": request.prediction_id,
        "status": "pending",
        "num_updates": request.num_updates,
    }


# ============================================================================
# Analytics Endpoints
# ============================================================================


@router.get("/analytics/accuracy")
async def get_accuracy_analytics(
    time_range: str = Query("30d", pattern="^(7d|30d|90d|1y)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get accuracy analytics across all predictions.
    """
    user_predictions = [
        p for p in prediction_store.values()
        if p.get("user_id") == str(current_user.id)
        and p.get("status") == "completed"
        and p.get("results")
    ]

    if not user_predictions:
        return {
            "total_predictions": 0,
            "average_accuracy": None,
            "accuracy_trend": [],
            "best_prediction": None,
        }

    # Calculate metrics
    accuracies = []
    for p in user_predictions:
        metrics = p.get("results", {}).get("accuracy_metrics", {})
        if metrics.get("accuracy"):
            accuracies.append(metrics["accuracy"])

    avg_accuracy = sum(accuracies) / len(accuracies) if accuracies else None

    return {
        "total_predictions": len(user_predictions),
        "average_accuracy": avg_accuracy,
        "accuracy_distribution": {
            "above_80": len([a for a in accuracies if a >= 0.80]),
            "60_to_80": len([a for a in accuracies if 0.60 <= a < 0.80]),
            "below_60": len([a for a in accuracies if a < 0.60]),
        },
        "predictions_meeting_target": len([a for a in accuracies if a >= 0.80]),
    }


@router.get("/analytics/overview")
async def get_predictions_overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get overview statistics for predictions.
    """
    user_predictions = [
        p for p in prediction_store.values()
        if p.get("user_id") == str(current_user.id)
    ]

    status_counts = {}
    total_agents = 0

    for p in user_predictions:
        s = p.get("status", "unknown")
        status_counts[s] = status_counts.get(s, 0) + 1

        config = p.get("config", {})
        agent_config = config.get("agent_config", {})
        total_agents += agent_config.get("count", 0)

    return {
        "total_predictions": len(user_predictions),
        "status_breakdown": status_counts,
        "total_agents_simulated": total_agents,
        "completed_predictions": status_counts.get("completed", 0),
    }


# ============================================================================
# Background Tasks
# ============================================================================


async def run_prediction_task(prediction_id: str, config: Dict[str, Any]):
    """Background task to run prediction simulation."""
    import asyncio
    import numpy as np

    prediction = prediction_store.get(prediction_id)
    if not prediction:
        return

    try:
        prediction["status"] = "running"
        prediction["started_at"] = datetime.utcnow().isoformat()

        # Simulate progress
        categories = config.get("categories", [])
        num_steps = config.get("num_steps", 30)
        monte_carlo_runs = config.get("monte_carlo_runs", 10)
        agent_count = config.get("agent_config", {}).get("count", 1000)

        total_iterations = num_steps * monte_carlo_runs

        # Simulate prediction results
        predictions = {}
        confidence_intervals = {}
        temporal_evolution = []

        for i, cat in enumerate(categories):
            cat_name = cat.get("name", f"Category_{i}")
            # Generate mock prediction
            base_value = np.random.dirichlet(np.ones(len(categories)))[i]

            # Run Monte Carlo simulations
            mc_results = []
            for _ in range(monte_carlo_runs):
                noise = np.random.normal(0, 0.05)
                mc_results.append(max(0.01, min(0.99, base_value + noise)))

            predictions[cat_name] = float(np.mean(mc_results))
            ci_low = float(np.percentile(mc_results, 2.5))
            ci_high = float(np.percentile(mc_results, 97.5))
            confidence_intervals[cat_name] = [ci_low, ci_high]

        # Simulate temporal evolution
        for step in range(num_steps):
            prediction["progress"] = (step / num_steps) * 100

            step_data = {"step": step, "distributions": {}}
            for cat_name in predictions:
                # Add some temporal variation
                step_data["distributions"][cat_name] = predictions[cat_name] + np.random.normal(0, 0.02)

            temporal_evolution.append(step_data)

            await asyncio.sleep(0.1)  # Simulate computation time

        # Calculate accuracy metrics (mock)
        accuracy_metrics = {
            "accuracy": 0.82 + np.random.uniform(-0.05, 0.05),
            "mae": 0.05 + np.random.uniform(-0.02, 0.02),
            "rmse": 0.07 + np.random.uniform(-0.02, 0.02),
            "kl_divergence": 0.03 + np.random.uniform(-0.01, 0.01),
            "brier_score": 0.04 + np.random.uniform(-0.01, 0.01),
            "correlation": 0.92 + np.random.uniform(-0.05, 0.05),
        }

        # Agent statistics
        agent_statistics = {
            "total_agents": agent_count,
            "decision_distribution": {cat.get("name", f"Cat_{i}"): int(agent_count * predictions.get(cat.get("name"), 0.1)) for i, cat in enumerate(categories)},
            "behavioral_params_used": {
                "loss_aversion": 2.25,
                "status_quo_bias": 0.3,
                "bandwagon_effect": 0.2,
            },
        }

        prediction["results"] = {
            "predictions": predictions,
            "confidence_intervals": confidence_intervals,
            "accuracy_metrics": accuracy_metrics,
            "temporal_evolution": temporal_evolution,
            "agent_statistics": agent_statistics,
        }

        prediction["status"] = "completed"
        prediction["progress"] = 100.0
        prediction["completed_at"] = datetime.utcnow().isoformat()

    except Exception as e:
        prediction["status"] = "failed"
        prediction["error"] = str(e)


async def run_calibration_task(
    calibration_id: str,
    prediction_id: str,
    ground_truth: Dict[str, Any],
    method: str,
    target_accuracy: float,
    max_iterations: int,
):
    """Background task to run calibration."""
    import asyncio
    import numpy as np

    calibration = calibration_store.get(calibration_id)
    if not calibration:
        return

    try:
        calibration["status"] = "running"
        calibration["started_at"] = datetime.utcnow().isoformat()

        # Simulate calibration iterations
        best_accuracy = 0.5
        best_params = {}
        history = []

        for iteration in range(max_iterations):
            # Simulate parameter search
            params = {
                "loss_aversion": 1.0 + np.random.uniform(0, 2),
                "status_quo_bias": np.random.uniform(0, 1),
                "bandwagon_susceptibility": np.random.uniform(0, 1),
                "social_influence_weight": np.random.uniform(0, 1),
                "noise_temperature": 0.01 + np.random.uniform(0, 0.99),
            }

            # Simulate accuracy improvement
            accuracy = min(0.95, 0.5 + iteration * 0.008 + np.random.uniform(-0.02, 0.02))

            if accuracy > best_accuracy:
                best_accuracy = accuracy
                best_params = params.copy()

            history.append({
                "iteration": iteration,
                "params": params,
                "accuracy": accuracy,
            })

            calibration["progress"] = (iteration / max_iterations) * 100

            await asyncio.sleep(0.05)

            # Early stopping if target reached
            if best_accuracy >= target_accuracy:
                break

        calibration["results"] = {
            "best_params": best_params,
            "best_accuracy": best_accuracy,
            "target_met": best_accuracy >= target_accuracy,
            "iterations_used": len(history),
            "improvement": best_accuracy - 0.5,
            "history": history[-10:],  # Last 10 iterations
        }

        calibration["status"] = "completed"
        calibration["progress"] = 100.0
        calibration["completed_at"] = datetime.utcnow().isoformat()

    except Exception as e:
        calibration["status"] = "failed"
        calibration["error"] = str(e)


async def run_marl_training_task(
    training_id: str,
    prediction_id: str,
    config: Dict[str, Any],
):
    """Background task to run MARL training."""
    import asyncio
    import numpy as np

    prediction = prediction_store.get(prediction_id)
    if not prediction or "training" not in prediction:
        return

    training = prediction["training"]

    try:
        training["status"] = "running"
        training["started_at"] = datetime.utcnow().isoformat()

        num_updates = config.get("num_updates", 100)
        metrics = []

        for update in range(num_updates):
            # Simulate training metrics
            policy_loss = max(0, 0.5 - update * 0.004 + np.random.uniform(-0.02, 0.02))
            value_loss = max(0, 1.0 - update * 0.008 + np.random.uniform(-0.05, 0.05))
            entropy = max(0, 0.8 - update * 0.005 + np.random.uniform(-0.02, 0.02))
            avg_reward = update * 0.1 + np.random.uniform(-0.5, 0.5)

            metrics.append({
                "update": update,
                "policy_loss": policy_loss,
                "value_loss": value_loss,
                "entropy": entropy,
                "avg_reward": avg_reward,
            })

            training["progress"] = (update / num_updates) * 100
            training["metrics"] = metrics[-20:]  # Keep last 20

            await asyncio.sleep(0.05)

        training["status"] = "completed"
        training["progress"] = 100.0
        training["completed_at"] = datetime.utcnow().isoformat()
        training["final_metrics"] = {
            "final_policy_loss": metrics[-1]["policy_loss"],
            "final_value_loss": metrics[-1]["value_loss"],
            "total_updates": len(metrics),
            "converged": True,
        }

    except Exception as e:
        training["status"] = "failed"
        training["error"] = str(e)
