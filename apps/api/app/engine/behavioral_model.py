"""
Behavioral Economics Model for Predictive Simulation

Implements cognitive biases, prospect theory, and behavioral decision-making.
Based on Kahneman-Tversky behavioral economics research.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class CognitiveBiases(str, Enum):
    """Supported cognitive biases."""
    LOSS_AVERSION = "loss_aversion"
    STATUS_QUO = "status_quo"
    CONFIRMATION = "confirmation"
    ANCHORING = "anchoring"
    BANDWAGON = "bandwagon"
    AVAILABILITY = "availability"
    FRAMING = "framing"
    OPTIMISM = "optimism"
    RECENCY = "recency"
    SOCIAL_PROOF = "social_proof"
    SUNK_COST = "sunk_cost"
    ENDOWMENT = "endowment"


@dataclass
class BehavioralParameters:
    """
    Behavioral economics parameters for an agent.
    Based on empirically validated behavioral economics research.
    """

    # Prospect Theory (Kahneman & Tversky)
    loss_aversion_lambda: float = 2.25  # λ in prospect theory, typical range 1.5-2.5
    reference_point: float = 0.0  # Current expectation level

    # Probability Weighting (Prelec function)
    probability_weight_alpha: float = 0.65  # Overweighting small probabilities
    probability_weight_beta: float = 0.60  # Underweighting large probabilities

    # Status Quo Bias
    status_quo_strength: float = 0.3  # 0-1, tendency to maintain current choice

    # Anchoring
    anchoring_strength: float = 0.5  # 0-1, weight given to initial beliefs

    # Confirmation Bias
    confirmation_bias: float = 0.4  # 0-1, tendency to seek confirming info

    # Bandwagon Effect
    bandwagon_susceptibility: float = 0.3  # 0-1, susceptibility to majority opinion

    # Availability Heuristic
    availability_weight: float = 0.5  # 0-1, weight given to recent/salient events

    # Bounded Rationality
    bounded_rationality: float = 0.6  # 0-1, cognitive limitations

    # Social Proof
    social_proof_weight: float = 0.4  # 0-1, influence of peer decisions

    # Time Discounting
    time_discount_factor: float = 0.95  # Exponential discount for future outcomes

    # Risk Preferences
    risk_aversion: float = 0.5  # 0-1, higher = more risk averse

    # Optimism/Pessimism
    optimism_bias: float = 0.0  # -1 to 1, positive = optimistic

    # Framing Effect
    framing_sensitivity: float = 0.3  # 0-1, susceptibility to framing

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            "loss_aversion_lambda": self.loss_aversion_lambda,
            "reference_point": self.reference_point,
            "probability_weight_alpha": self.probability_weight_alpha,
            "probability_weight_beta": self.probability_weight_beta,
            "status_quo_strength": self.status_quo_strength,
            "anchoring_strength": self.anchoring_strength,
            "confirmation_bias": self.confirmation_bias,
            "bandwagon_susceptibility": self.bandwagon_susceptibility,
            "availability_weight": self.availability_weight,
            "bounded_rationality": self.bounded_rationality,
            "social_proof_weight": self.social_proof_weight,
            "time_discount_factor": self.time_discount_factor,
            "risk_aversion": self.risk_aversion,
            "optimism_bias": self.optimism_bias,
            "framing_sensitivity": self.framing_sensitivity,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> "BehavioralParameters":
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})


class BehavioralModel:
    """
    Implements behavioral economics decision-making model.
    Supports vectorized operations for batch processing of 10,000+ agents.
    """

    def __init__(self, epsilon: float = 1e-10):
        """
        Initialize behavioral model.

        Args:
            epsilon: Small value to prevent division by zero
        """
        self.epsilon = epsilon

    # ==================== PROSPECT THEORY ====================

    def value_function(
        self,
        outcomes: np.ndarray,
        reference_points: np.ndarray,
        loss_aversion: np.ndarray,
        alpha: float = 0.88,  # Diminishing sensitivity parameter
    ) -> np.ndarray:
        """
        Kahneman-Tversky value function.
        v(x) = x^α for gains, v(x) = -λ(-x)^α for losses

        Args:
            outcomes: Shape (batch_size,) or (batch_size, num_outcomes)
            reference_points: Shape (batch_size,) - reference points
            loss_aversion: Shape (batch_size,) - λ values
            alpha: Diminishing sensitivity parameter

        Returns:
            Subjective values with same shape as outcomes
        """
        # Calculate gains and losses relative to reference point
        if outcomes.ndim == 1:
            deviations = outcomes - reference_points
        else:
            deviations = outcomes - reference_points[:, np.newaxis]

        # Separate gains and losses
        gains = np.maximum(deviations, 0)
        losses = np.minimum(deviations, 0)

        # Apply value function
        gain_values = np.power(gains, alpha)

        if outcomes.ndim == 1:
            loss_values = -loss_aversion * np.power(-losses, alpha)
        else:
            loss_values = -loss_aversion[:, np.newaxis] * np.power(-losses, alpha)

        return np.where(deviations >= 0, gain_values, loss_values)

    def probability_weight(
        self,
        probabilities: np.ndarray,
        alpha: np.ndarray,
        beta: np.ndarray,
    ) -> np.ndarray:
        """
        Prelec probability weighting function.
        w(p) = exp(-β(-ln(p))^α)

        Args:
            probabilities: Shape (batch_size,) or (batch_size, num_options)
            alpha: Shape (batch_size,) - curvature parameter
            beta: Shape (batch_size,) - elevation parameter

        Returns:
            Weighted probabilities
        """
        # Clip to avoid log(0)
        p = np.clip(probabilities, self.epsilon, 1 - self.epsilon)

        if p.ndim == 1:
            # Single dimension
            return np.exp(-beta * np.power(-np.log(p), alpha))
        else:
            # Multiple options per agent
            log_p = -np.log(p)
            power_term = np.power(log_p, alpha[:, np.newaxis])
            return np.exp(-beta[:, np.newaxis] * power_term)

    def prospect_theory_utility(
        self,
        outcomes: np.ndarray,
        probabilities: np.ndarray,
        params: Dict[str, np.ndarray],
    ) -> np.ndarray:
        """
        Calculate prospect theory utility for risky choices.

        Args:
            outcomes: Shape (batch_size, num_options) - outcome values
            probabilities: Shape (batch_size, num_options) - probabilities
            params: Dict with arrays for behavioral parameters

        Returns:
            Shape (batch_size, num_options) - prospect theory utilities
        """
        # Get parameters
        reference = params.get("reference_point", np.zeros(outcomes.shape[0]))
        lambda_loss = params.get("loss_aversion_lambda", np.full(outcomes.shape[0], 2.25))
        alpha_prob = params.get("probability_weight_alpha", np.full(outcomes.shape[0], 0.65))
        beta_prob = params.get("probability_weight_beta", np.full(outcomes.shape[0], 0.60))

        # Calculate subjective values
        values = self.value_function(outcomes, reference, lambda_loss)

        # Calculate weighted probabilities
        weighted_probs = self.probability_weight(probabilities, alpha_prob, beta_prob)

        # Prospect theory utility = weighted probability × value
        return weighted_probs * values

    # ==================== COGNITIVE BIASES ====================

    def apply_status_quo_bias(
        self,
        action_utilities: np.ndarray,
        current_choices: np.ndarray,
        bias_strength: np.ndarray,
        boost_factor: float = 0.3,
    ) -> np.ndarray:
        """
        Apply status quo bias - boost utility of current choice.

        Args:
            action_utilities: Shape (batch_size, num_actions)
            current_choices: Shape (batch_size,) - current choice indices (-1 for none)
            bias_strength: Shape (batch_size,) - strength of bias
            boost_factor: Base boost to current choice

        Returns:
            Modified utilities
        """
        result = action_utilities.copy()

        # Find agents with existing choices
        has_choice = current_choices >= 0
        if not has_choice.any():
            return result

        # Boost utility of current choice
        for i in range(result.shape[0]):
            if has_choice[i]:
                current = int(current_choices[i])
                if 0 <= current < result.shape[1]:
                    result[i, current] += boost_factor * bias_strength[i]

        return result

    def apply_anchoring(
        self,
        current_beliefs: np.ndarray,
        new_information: np.ndarray,
        anchoring_strength: np.ndarray,
    ) -> np.ndarray:
        """
        Apply anchoring bias - weight current beliefs vs new information.

        Args:
            current_beliefs: Shape (batch_size, dimensions)
            new_information: Shape (batch_size, dimensions)
            anchoring_strength: Shape (batch_size,) - how strongly anchored

        Returns:
            Updated beliefs
        """
        # Stronger anchoring = more weight on current beliefs
        anchor_weight = anchoring_strength[:, np.newaxis]
        new_weight = 1 - anchor_weight

        return (current_beliefs * anchor_weight) + (new_information * new_weight)

    def apply_confirmation_bias(
        self,
        information_values: np.ndarray,
        current_preferences: np.ndarray,
        confirmation_strength: np.ndarray,
    ) -> np.ndarray:
        """
        Apply confirmation bias - inflate value of confirming information.

        Args:
            information_values: Shape (batch_size, num_info) - information values
            current_preferences: Shape (batch_size, num_options) - current beliefs
            confirmation_strength: Shape (batch_size,)

        Returns:
            Biased information values
        """
        # Determine preferred option
        preferred = current_preferences.argmax(axis=1)

        # Boost information that confirms preferred option
        # (simplified: boost columns matching preferred index)
        result = information_values.copy()

        for i in range(result.shape[0]):
            pref_idx = preferred[i]
            if pref_idx < result.shape[1]:
                # Confirming info gets boosted
                result[i, pref_idx] *= (1 + confirmation_strength[i] * 0.5)
                # Disconfirming info gets discounted
                for j in range(result.shape[1]):
                    if j != pref_idx:
                        result[i, j] *= (1 - confirmation_strength[i] * 0.3)

        return result

    def apply_bandwagon_effect(
        self,
        action_utilities: np.ndarray,
        population_distribution: np.ndarray,
        bandwagon_susceptibility: np.ndarray,
        intensity_factor: float = 0.5,
    ) -> np.ndarray:
        """
        Apply bandwagon effect - boost popularity of majority choice.

        Args:
            action_utilities: Shape (batch_size, num_actions)
            population_distribution: Shape (num_actions,) - population choice distribution
            bandwagon_susceptibility: Shape (batch_size,)
            intensity_factor: Strength of bandwagon boost

        Returns:
            Modified utilities
        """
        # Normalize distribution
        pop_dist = population_distribution / (population_distribution.sum() + self.epsilon)

        # Calculate bandwagon boost (more for popular options)
        bandwagon_boost = pop_dist * intensity_factor

        # Apply based on individual susceptibility
        boost_matrix = bandwagon_susceptibility[:, np.newaxis] * bandwagon_boost

        return action_utilities + boost_matrix

    def apply_availability_heuristic(
        self,
        event_importance: np.ndarray,
        recency_weights: np.ndarray,
        availability_strength: np.ndarray,
    ) -> np.ndarray:
        """
        Apply availability heuristic - overweight recent/salient events.

        Args:
            event_importance: Shape (batch_size, num_events) - objective importance
            recency_weights: Shape (num_events,) - how recent (1 = most recent)
            availability_strength: Shape (batch_size,)

        Returns:
            Perceived importance
        """
        # Calculate availability boost from recency
        recency_boost = np.power(recency_weights, 2)  # Square to amplify recent events

        # Apply availability bias
        biased_importance = event_importance * (1 + availability_strength[:, np.newaxis] * recency_boost)

        return biased_importance

    def apply_social_proof(
        self,
        action_utilities: np.ndarray,
        peer_choices: np.ndarray,
        social_weights: np.ndarray,
        social_proof_strength: np.ndarray,
    ) -> np.ndarray:
        """
        Apply social proof - influenced by peer decisions.

        Args:
            action_utilities: Shape (batch_size, num_actions)
            peer_choices: Shape (batch_size, num_peers) - peer choice indices
            social_weights: Shape (batch_size, num_peers) - influence weight per peer
            social_proof_strength: Shape (batch_size,)

        Returns:
            Modified utilities
        """
        num_agents, num_actions = action_utilities.shape
        result = action_utilities.copy()

        for i in range(num_agents):
            if social_proof_strength[i] < 0.01:
                continue

            # Count peer votes for each action, weighted by social influence
            peer_support = np.zeros(num_actions)
            total_weight = 0

            for j, peer_choice in enumerate(peer_choices[i]):
                if peer_choice >= 0 and peer_choice < num_actions:
                    weight = social_weights[i, j] if j < len(social_weights[i]) else 0.1
                    peer_support[int(peer_choice)] += weight
                    total_weight += weight

            if total_weight > 0:
                peer_support /= total_weight
                result[i] += social_proof_strength[i] * peer_support * 0.5

        return result

    def apply_framing_effect(
        self,
        action_utilities: np.ndarray,
        framing_valence: np.ndarray,
        framing_sensitivity: np.ndarray,
    ) -> np.ndarray:
        """
        Apply framing effect - how options are presented affects perception.

        Args:
            action_utilities: Shape (batch_size, num_actions)
            framing_valence: Shape (num_actions,) - positive (1) vs negative (-1) framing
            framing_sensitivity: Shape (batch_size,)

        Returns:
            Modified utilities
        """
        # Framing boost/penalty
        framing_adjustment = framing_valence * framing_sensitivity[:, np.newaxis] * 0.2

        return action_utilities + framing_adjustment

    def apply_recency_bias(
        self,
        action_utilities: np.ndarray,
        recent_outcomes: np.ndarray,
        recency_strength: np.ndarray,
        decay_factor: float = 0.8,
    ) -> np.ndarray:
        """
        Apply recency bias - overweight recent experiences.

        Args:
            action_utilities: Shape (batch_size, num_actions)
            recent_outcomes: Shape (batch_size, history_length, num_actions) - recent rewards
            recency_strength: Shape (batch_size,)
            decay_factor: How quickly past experiences decay

        Returns:
            Modified utilities
        """
        if recent_outcomes.shape[1] == 0:
            return action_utilities

        # Calculate decay weights (most recent = highest weight)
        history_len = recent_outcomes.shape[1]
        time_weights = np.array([decay_factor ** i for i in range(history_len - 1, -1, -1)])

        # Weighted average of recent outcomes
        weighted_outcomes = (recent_outcomes * time_weights[np.newaxis, :, np.newaxis]).sum(axis=1)
        weighted_outcomes /= (time_weights.sum() + self.epsilon)

        # Apply recency adjustment
        recency_adjustment = recency_strength[:, np.newaxis] * weighted_outcomes * 0.3

        return action_utilities + recency_adjustment

    # ==================== COMPOSITE DECISION MODEL ====================

    def compute_decision_utilities(
        self,
        base_utilities: np.ndarray,
        behavioral_params: Dict[str, np.ndarray],
        context: Dict[str, np.ndarray],
        active_biases: Optional[List[CognitiveBiases]] = None,
    ) -> np.ndarray:
        """
        Compute final decision utilities with all applicable biases.

        Args:
            base_utilities: Shape (batch_size, num_actions) - rational utilities
            behavioral_params: Dict of parameter arrays
            context: Dict of contextual information
            active_biases: List of biases to apply (default: all applicable)

        Returns:
            Final utilities incorporating behavioral economics
        """
        utilities = base_utilities.copy()

        if active_biases is None:
            active_biases = list(CognitiveBiases)

        # Status quo bias
        if CognitiveBiases.STATUS_QUO in active_biases and "current_choices" in context:
            utilities = self.apply_status_quo_bias(
                utilities,
                context["current_choices"],
                behavioral_params.get("status_quo_strength", np.full(utilities.shape[0], 0.3)),
            )

        # Bandwagon effect
        if CognitiveBiases.BANDWAGON in active_biases and "population_distribution" in context:
            utilities = self.apply_bandwagon_effect(
                utilities,
                context["population_distribution"],
                behavioral_params.get("bandwagon_susceptibility", np.full(utilities.shape[0], 0.3)),
            )

        # Social proof
        if CognitiveBiases.SOCIAL_PROOF in active_biases and "peer_choices" in context:
            utilities = self.apply_social_proof(
                utilities,
                context["peer_choices"],
                context.get("social_weights", np.ones((utilities.shape[0], 10)) * 0.1),
                behavioral_params.get("social_proof_weight", np.full(utilities.shape[0], 0.4)),
            )

        # Framing effect
        if CognitiveBiases.FRAMING in active_biases and "framing_valence" in context:
            utilities = self.apply_framing_effect(
                utilities,
                context["framing_valence"],
                behavioral_params.get("framing_sensitivity", np.full(utilities.shape[0], 0.3)),
            )

        # Recency bias
        if CognitiveBiases.RECENCY in active_biases and "recent_outcomes" in context:
            utilities = self.apply_recency_bias(
                utilities,
                context["recent_outcomes"],
                behavioral_params.get("availability_weight", np.full(utilities.shape[0], 0.5)),
            )

        # Apply bounded rationality noise
        if "bounded_rationality" in behavioral_params:
            noise_scale = behavioral_params["bounded_rationality"] * 0.1
            noise = np.random.normal(0, noise_scale[:, np.newaxis], utilities.shape)
            utilities += noise

        return utilities

    def make_decisions(
        self,
        utilities: np.ndarray,
        temperature: float = 1.0,
        deterministic: bool = False,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Make decisions based on utilities using softmax selection.

        Args:
            utilities: Shape (batch_size, num_actions)
            temperature: Softmax temperature (lower = more deterministic)
            deterministic: If True, always select max utility

        Returns:
            Tuple of (choices, probabilities)
        """
        if deterministic:
            choices = utilities.argmax(axis=1)
            probs = np.zeros_like(utilities)
            probs[np.arange(len(choices)), choices] = 1.0
            return choices, probs

        # Softmax with temperature
        scaled = utilities / (temperature + self.epsilon)
        # Numerical stability: subtract max
        scaled = scaled - scaled.max(axis=1, keepdims=True)
        exp_scaled = np.exp(scaled)
        probs = exp_scaled / (exp_scaled.sum(axis=1, keepdims=True) + self.epsilon)

        # Sample from probability distribution
        choices = np.array([
            np.random.choice(len(p), p=p)
            for p in probs
        ])

        return choices, probs

    def update_beliefs(
        self,
        current_beliefs: np.ndarray,
        new_evidence: np.ndarray,
        evidence_strength: np.ndarray,
        behavioral_params: Dict[str, np.ndarray],
    ) -> np.ndarray:
        """
        Update beliefs incorporating behavioral biases.

        Args:
            current_beliefs: Shape (batch_size, num_beliefs)
            new_evidence: Shape (batch_size, num_beliefs)
            evidence_strength: Shape (batch_size,) - how strong the evidence is
            behavioral_params: Dict of behavioral parameters

        Returns:
            Updated beliefs
        """
        # Apply anchoring - weight toward current beliefs
        anchoring = behavioral_params.get("anchoring_strength", np.full(current_beliefs.shape[0], 0.5))

        # Apply confirmation bias - inflate confirming evidence
        confirmation = behavioral_params.get("confirmation_bias", np.full(current_beliefs.shape[0], 0.4))

        # Find current best belief for each agent
        current_best = current_beliefs.argmax(axis=1)

        # Adjust evidence based on confirmation bias
        adjusted_evidence = new_evidence.copy()
        for i in range(len(current_best)):
            best_idx = current_best[i]
            # Boost confirming evidence
            adjusted_evidence[i, best_idx] *= (1 + confirmation[i] * 0.3)
            # Discount disconfirming evidence
            for j in range(adjusted_evidence.shape[1]):
                if j != best_idx:
                    adjusted_evidence[i, j] *= (1 - confirmation[i] * 0.2)

        # Weighted update with anchoring
        update_weight = evidence_strength * (1 - anchoring)
        updated = current_beliefs * (1 - update_weight[:, np.newaxis]) + \
                  adjusted_evidence * update_weight[:, np.newaxis]

        # Normalize to ensure valid probability distribution
        updated = np.clip(updated, 0, None)
        row_sums = updated.sum(axis=1, keepdims=True)
        row_sums = np.where(row_sums > 0, row_sums, 1)
        updated = updated / row_sums

        return updated


@dataclass
class SocialInfluenceModel:
    """
    Models social influence between agents.
    Implements homophily, opinion dynamics, and information cascade effects.
    """

    # Influence decay with network distance
    distance_decay: float = 0.5

    # Homophily strength
    homophily_weight: float = 0.7

    # Conformity pressure
    conformity_strength: float = 0.3

    # Information cascade threshold
    cascade_threshold: float = 0.6

    def compute_social_influence(
        self,
        agent_states: np.ndarray,
        adjacency_matrix: np.ndarray,
        influence_weights: np.ndarray,
    ) -> np.ndarray:
        """
        Compute social influence on agent beliefs.

        Args:
            agent_states: Shape (num_agents, state_dim)
            adjacency_matrix: Shape (num_agents, num_agents) - sparse
            influence_weights: Shape (num_agents, num_agents)

        Returns:
            Influence vector for each agent
        """
        # Weighted average of neighbor states
        weighted_adj = adjacency_matrix * influence_weights

        # Normalize by total influence received
        row_sums = weighted_adj.sum(axis=1, keepdims=True)
        row_sums = np.where(row_sums > 0, row_sums, 1)
        normalized_adj = weighted_adj / row_sums

        # Compute influence: average of connected neighbors
        influence = normalized_adj @ agent_states

        return influence

    def detect_information_cascade(
        self,
        agent_choices: np.ndarray,
        adjacency_matrix: np.ndarray,
        threshold: Optional[float] = None,
    ) -> np.ndarray:
        """
        Detect if agents are in information cascade (following others blindly).

        Args:
            agent_choices: Shape (num_agents,) - current choices
            adjacency_matrix: Shape (num_agents, num_agents)
            threshold: Cascade detection threshold

        Returns:
            Boolean mask of agents in cascade
        """
        threshold = threshold or self.cascade_threshold
        num_agents = len(agent_choices)
        in_cascade = np.zeros(num_agents, dtype=bool)

        for i in range(num_agents):
            if agent_choices[i] < 0:
                continue

            # Get neighbor choices
            neighbors = np.where(adjacency_matrix[i] > 0)[0]
            if len(neighbors) == 0:
                continue

            neighbor_choices = agent_choices[neighbors]
            valid_neighbors = neighbor_choices >= 0

            if valid_neighbors.sum() == 0:
                continue

            # Check if majority of neighbors made same choice
            same_choice = (neighbor_choices[valid_neighbors] == agent_choices[i]).mean()
            in_cascade[i] = same_choice >= threshold

        return in_cascade

    def compute_homophily_score(
        self,
        agent_i_features: np.ndarray,
        agent_j_features: np.ndarray,
    ) -> float:
        """
        Compute homophily (similarity) score between two agents.

        Args:
            agent_i_features: Features of agent i
            agent_j_features: Features of agent j

        Returns:
            Similarity score 0-1
        """
        # Cosine similarity
        dot_product = np.dot(agent_i_features, agent_j_features)
        norm_i = np.linalg.norm(agent_i_features)
        norm_j = np.linalg.norm(agent_j_features)

        if norm_i < 1e-10 or norm_j < 1e-10:
            return 0.0

        similarity = dot_product / (norm_i * norm_j)

        # Scale to 0-1
        return (similarity + 1) / 2


def create_default_behavioral_params(
    num_agents: int,
    profile: str = "average",
    randomize: bool = True,
) -> Dict[str, np.ndarray]:
    """
    Create default behavioral parameters for a population.

    Args:
        num_agents: Number of agents
        profile: Population profile ("average", "rational", "emotional", "mixed")
        randomize: Add random variation

    Returns:
        Dict of parameter arrays
    """
    params = {}

    # Base values by profile
    profiles = {
        "average": {
            "loss_aversion_lambda": 2.25,
            "probability_weight_alpha": 0.65,
            "probability_weight_beta": 0.60,
            "status_quo_strength": 0.3,
            "anchoring_strength": 0.5,
            "confirmation_bias": 0.4,
            "bandwagon_susceptibility": 0.3,
            "availability_weight": 0.5,
            "bounded_rationality": 0.6,
            "social_proof_weight": 0.4,
            "risk_aversion": 0.5,
        },
        "rational": {
            "loss_aversion_lambda": 1.5,
            "probability_weight_alpha": 0.9,
            "probability_weight_beta": 0.9,
            "status_quo_strength": 0.1,
            "anchoring_strength": 0.2,
            "confirmation_bias": 0.1,
            "bandwagon_susceptibility": 0.1,
            "availability_weight": 0.2,
            "bounded_rationality": 0.2,
            "social_proof_weight": 0.1,
            "risk_aversion": 0.3,
        },
        "emotional": {
            "loss_aversion_lambda": 3.0,
            "probability_weight_alpha": 0.5,
            "probability_weight_beta": 0.5,
            "status_quo_strength": 0.5,
            "anchoring_strength": 0.7,
            "confirmation_bias": 0.6,
            "bandwagon_susceptibility": 0.5,
            "availability_weight": 0.7,
            "bounded_rationality": 0.8,
            "social_proof_weight": 0.6,
            "risk_aversion": 0.7,
        },
    }

    base = profiles.get(profile, profiles["average"])

    for key, value in base.items():
        if randomize:
            # Add normal variation (10-20% std)
            std = value * 0.15
            params[key] = np.random.normal(value, std, num_agents)
            # Clip to valid ranges
            if "lambda" in key:
                params[key] = np.clip(params[key], 1.0, 4.0)
            elif "alpha" in key or "beta" in key:
                params[key] = np.clip(params[key], 0.3, 1.0)
            else:
                params[key] = np.clip(params[key], 0.0, 1.0)
        else:
            params[key] = np.full(num_agents, value)

    # Add reference point (starts at 0)
    params["reference_point"] = np.zeros(num_agents)

    return params
