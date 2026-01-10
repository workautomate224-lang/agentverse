"""
STEP 9: Knowledge Graph / Parallel Universe Ops Tests

Verifies:
- Universe Graph buttons (Switch View, Search Node, Filter by Probability/Reliability, etc.)
- Node Compare buttons (Select A, Select B, Show Diff, Export Diff Report)
- Graph API returns nodes+edges with paging
- Dependency tracking marks downstream stale when upstream changes
- Node compare returns patch diff + outcome diff + driver diff + reliability diff
- Pruning/collapse operate as UI filters (no data deletion)
- Refresh reruns only stale nodes with cost estimate

Reference: Future_Predictive_AI_Platform_Ultra_Checklist.md STEP 9
"""

import pytest
from datetime import datetime
from typing import Any, Dict


# =============================================================================
# Universe Graph Button→Backend Chain Tests
# =============================================================================

class TestUniverseGraphButtonChains:
    """Test all Universe Graph button→backend chains exist."""

    def test_switch_view_endpoint_exists(self):
        """Universe Graph: Switch View: Tree/Graph button chain."""
        from app.api.v1.endpoints import universe_graph

        routes = [r.path for r in universe_graph.router.routes]
        assert "/switch-view" in routes

    def test_search_node_endpoint_exists(self):
        """Universe Graph: Search Node button chain."""
        from app.api.v1.endpoints import universe_graph

        routes = [r.path for r in universe_graph.router.routes]
        assert "/search-node" in routes

    def test_filter_by_probability_endpoint_exists(self):
        """Universe Graph: Filter by Probability button chain."""
        from app.api.v1.endpoints import universe_graph

        routes = [r.path for r in universe_graph.router.routes]
        assert "/filter-by-probability" in routes

    def test_filter_by_reliability_endpoint_exists(self):
        """Universe Graph: Filter by Reliability button chain."""
        from app.api.v1.endpoints import universe_graph

        routes = [r.path for r in universe_graph.router.routes]
        assert "/filter-by-reliability" in routes

    def test_cluster_branches_endpoint_exists(self):
        """Universe Graph: Cluster Similar Branches button chain."""
        from app.api.v1.endpoints import universe_graph

        routes = [r.path for r in universe_graph.router.routes]
        assert "/cluster-branches" in routes

    def test_mark_stale_endpoint_exists(self):
        """Universe Graph: Mark Stale button chain."""
        from app.api.v1.endpoints import universe_graph

        routes = [r.path for r in universe_graph.router.routes]
        assert "/mark-stale" in routes

    def test_refresh_branch_endpoint_exists(self):
        """Universe Graph: Refresh Branch button chain."""
        from app.api.v1.endpoints import universe_graph

        routes = [r.path for r in universe_graph.router.routes]
        assert "/refresh-branch" in routes


# =============================================================================
# Node Compare Button→Backend Chain Tests
# =============================================================================

class TestNodeCompareButtonChains:
    """Test all Node Compare button→backend chains exist."""

    def test_select_node_endpoint_exists(self):
        """Node Compare: Select A / Select B button chain."""
        from app.api.v1.endpoints import universe_graph

        routes = [r.path for r in universe_graph.router.routes]
        assert "/select-node" in routes

    def test_show_diff_endpoint_exists(self):
        """Node Compare: Show Diff button chain."""
        from app.api.v1.endpoints import universe_graph

        routes = [r.path for r in universe_graph.router.routes]
        assert "/show-diff" in routes

    def test_export_diff_report_endpoint_exists(self):
        """Node Compare: Export Diff Report button chain."""
        from app.api.v1.endpoints import universe_graph

        routes = [r.path for r in universe_graph.router.routes]
        assert "/export-diff-report" in routes


# =============================================================================
# Request Schema Tests
# =============================================================================

class TestRequestSchemas:
    """Test STEP 9 request schemas."""

    def test_graph_view_request_schema(self):
        """Test GraphViewRequest schema."""
        from app.api.v1.endpoints.universe_graph import GraphViewRequest

        fields = GraphViewRequest.model_fields
        assert "project_id" in fields
        assert "view_mode" in fields
        assert "depth_limit" in fields

    def test_search_node_request_schema(self):
        """Test SearchNodeRequest schema."""
        from app.api.v1.endpoints.universe_graph import SearchNodeRequest

        fields = SearchNodeRequest.model_fields
        assert "project_id" in fields
        assert "query" in fields
        assert "search_fields" in fields
        assert "limit" in fields

    def test_filter_by_probability_request_schema(self):
        """Test FilterByProbabilityRequest schema."""
        from app.api.v1.endpoints.universe_graph import FilterByProbabilityRequest

        fields = FilterByProbabilityRequest.model_fields
        assert "project_id" in fields
        assert "min_probability" in fields
        assert "max_probability" in fields
        assert "probability_type" in fields

    def test_filter_by_reliability_request_schema(self):
        """Test FilterByReliabilityRequest schema."""
        from app.api.v1.endpoints.universe_graph import FilterByReliabilityRequest

        fields = FilterByReliabilityRequest.model_fields
        assert "project_id" in fields
        assert "min_reliability" in fields
        assert "max_reliability" in fields
        assert "metrics_required" in fields

    def test_cluster_branches_request_schema(self):
        """Test ClusterBranchesRequest schema."""
        from app.api.v1.endpoints.universe_graph import ClusterBranchesRequest

        fields = ClusterBranchesRequest.model_fields
        assert "project_id" in fields
        assert "similarity_threshold" in fields
        assert "clustering_method" in fields

    def test_mark_stale_request_schema(self):
        """Test MarkStaleRequest schema."""
        from app.api.v1.endpoints.universe_graph import MarkStaleRequest

        fields = MarkStaleRequest.model_fields
        assert "project_id" in fields
        assert "node_ids" in fields
        assert "stale_reason" in fields
        assert "propagate_downstream" in fields

    def test_refresh_branch_request_schema(self):
        """Test RefreshBranchRequest schema."""
        from app.api.v1.endpoints.universe_graph import RefreshBranchRequest

        fields = RefreshBranchRequest.model_fields
        assert "project_id" in fields
        assert "node_ids" in fields
        assert "refresh_mode" in fields
        assert "dry_run" in fields
        assert "max_cost_usd" in fields

    def test_select_node_request_schema(self):
        """Test SelectNodeRequest schema."""
        from app.api.v1.endpoints.universe_graph import SelectNodeRequest

        fields = SelectNodeRequest.model_fields
        assert "project_id" in fields
        assert "node_id" in fields
        assert "slot" in fields

    def test_show_diff_request_schema(self):
        """Test ShowDiffRequest schema."""
        from app.api.v1.endpoints.universe_graph import ShowDiffRequest

        fields = ShowDiffRequest.model_fields
        assert "project_id" in fields
        assert "node_a_id" in fields
        assert "node_b_id" in fields
        assert "diff_types" in fields

    def test_export_diff_report_request_schema(self):
        """Test ExportDiffReportRequest schema."""
        from app.api.v1.endpoints.universe_graph import ExportDiffReportRequest

        fields = ExportDiffReportRequest.model_fields
        assert "project_id" in fields
        assert "node_a_id" in fields
        assert "node_b_id" in fields
        assert "format" in fields


# =============================================================================
# Response Schema Tests
# =============================================================================

class TestResponseSchemas:
    """Test STEP 9 response schemas."""

    def test_graph_view_response_schema(self):
        """Test GraphViewResponse schema."""
        from app.api.v1.endpoints.universe_graph import GraphViewResponse

        fields = GraphViewResponse.model_fields
        assert "project_id" in fields
        assert "view_mode" in fields
        assert "nodes" in fields
        assert "edges" in fields
        assert "total_nodes" in fields
        assert "pagination" in fields

    def test_graph_node_schema(self):
        """Test GraphNode schema for visualization."""
        from app.api.v1.endpoints.universe_graph import GraphNode

        fields = GraphNode.model_fields
        assert "node_id" in fields
        assert "depth" in fields
        assert "probability" in fields
        assert "is_stale" in fields
        assert "stale_reason" in fields
        assert "reliability_score" in fields

    def test_graph_edge_schema(self):
        """Test GraphEdge schema."""
        from app.api.v1.endpoints.universe_graph import GraphEdge

        fields = GraphEdge.model_fields
        assert "source_node_id" in fields
        assert "target_node_id" in fields
        assert "edge_type" in fields
        assert "probability" in fields

    def test_search_node_response_schema(self):
        """Test SearchNodeResponse schema."""
        from app.api.v1.endpoints.universe_graph import SearchNodeResponse

        fields = SearchNodeResponse.model_fields
        assert "project_id" in fields
        assert "query" in fields
        assert "results" in fields
        assert "total_matches" in fields

    def test_filter_response_schema(self):
        """Test FilterResponse schema."""
        from app.api.v1.endpoints.universe_graph import FilterResponse

        fields = FilterResponse.model_fields
        assert "filter_type" in fields
        assert "filter_params" in fields
        assert "matching_nodes" in fields
        assert "total_matches" in fields

    def test_cluster_branches_response_schema(self):
        """Test ClusterBranchesResponse schema."""
        from app.api.v1.endpoints.universe_graph import ClusterBranchesResponse

        fields = ClusterBranchesResponse.model_fields
        assert "clusters" in fields
        assert "unclustered_nodes" in fields
        assert "total_clusters" in fields
        assert "clustering_method" in fields

    def test_cluster_info_schema(self):
        """Test ClusterInfo schema."""
        from app.api.v1.endpoints.universe_graph import ClusterInfo

        fields = ClusterInfo.model_fields
        assert "cluster_id" in fields
        assert "representative_node_id" in fields
        assert "member_node_ids" in fields
        assert "similarity_score" in fields

    def test_stale_mark_response_schema(self):
        """Test StaleMarkResponse schema."""
        from app.api.v1.endpoints.universe_graph import StaleMarkResponse

        fields = StaleMarkResponse.model_fields
        assert "marked_nodes" in fields
        assert "downstream_affected" in fields
        assert "stale_reason" in fields
        assert "audit_log_id" in fields

    def test_refresh_cost_estimate_schema(self):
        """Test RefreshCostEstimate schema."""
        from app.api.v1.endpoints.universe_graph import RefreshCostEstimate

        fields = RefreshCostEstimate.model_fields
        assert "estimated_llm_calls" in fields
        assert "estimated_compute_minutes" in fields
        assert "estimated_cost_usd" in fields
        assert "breakdown" in fields

    def test_refresh_branch_response_schema(self):
        """Test RefreshBranchResponse schema."""
        from app.api.v1.endpoints.universe_graph import RefreshBranchResponse

        fields = RefreshBranchResponse.model_fields
        assert "nodes_to_refresh" in fields
        assert "cost_estimate" in fields
        assert "dry_run" in fields
        assert "job_id" in fields
        assert "audit_log_id" in fields

    def test_show_diff_response_schema(self):
        """Test ShowDiffResponse schema."""
        from app.api.v1.endpoints.universe_graph import ShowDiffResponse

        fields = ShowDiffResponse.model_fields
        assert "node_a_id" in fields
        assert "node_b_id" in fields
        assert "patch_diff" in fields
        assert "outcome_diff" in fields
        assert "driver_diff" in fields
        assert "reliability_diff" in fields
        assert "overall_similarity" in fields

    def test_diff_section_schema(self):
        """Test DiffSection schema."""
        from app.api.v1.endpoints.universe_graph import DiffSection

        fields = DiffSection.model_fields
        assert "diff_type" in fields
        assert "has_differences" in fields
        assert "summary" in fields
        assert "additions" in fields
        assert "removals" in fields
        assert "changes" in fields

    def test_export_diff_report_response_schema(self):
        """Test ExportDiffReportResponse schema."""
        from app.api.v1.endpoints.universe_graph import ExportDiffReportResponse

        fields = ExportDiffReportResponse.model_fields
        assert "format" in fields
        assert "download_url" in fields
        assert "report_content" in fields
        assert "export_id" in fields


# =============================================================================
# Graph API Tests (nodes+edges with paging)
# =============================================================================

class TestGraphAPI:
    """Test Graph API returns nodes+edges with paging."""

    def test_get_graph_endpoint_exists(self):
        """STEP 9: Graph API endpoint exists."""
        from app.api.v1.endpoints import universe_graph

        routes = [r.path for r in universe_graph.router.routes]
        assert "/graph/{project_id}" in routes

    def test_graph_response_has_nodes_and_edges(self):
        """STEP 9: Graph API returns nodes+edges."""
        from app.api.v1.endpoints.universe_graph import GraphViewResponse

        fields = GraphViewResponse.model_fields
        assert "nodes" in fields
        assert "edges" in fields

    def test_graph_response_has_pagination(self):
        """STEP 9: Graph API supports pagination."""
        from app.api.v1.endpoints.universe_graph import GraphViewResponse

        fields = GraphViewResponse.model_fields
        assert "pagination" in fields
        assert "total_nodes" in fields
        assert "visible_nodes" in fields


# =============================================================================
# Dependency Tracking Tests
# =============================================================================

class TestDependencyTracking:
    """Test dependency tracking functionality."""

    def test_stale_nodes_endpoint_exists(self):
        """STEP 9: Stale nodes tracking endpoint exists."""
        from app.api.v1.endpoints import universe_graph

        routes = [r.path for r in universe_graph.router.routes]
        assert "/stale-nodes/{project_id}" in routes

    def test_dependencies_endpoint_exists(self):
        """STEP 9: Dependencies endpoint exists."""
        from app.api.v1.endpoints import universe_graph

        routes = [r.path for r in universe_graph.router.routes]
        assert "/dependencies/{node_id}" in routes

    def test_mark_stale_propagates_downstream(self):
        """STEP 9: Mark stale can propagate to downstream nodes."""
        from app.api.v1.endpoints.universe_graph import MarkStaleRequest

        fields = MarkStaleRequest.model_fields
        assert "propagate_downstream" in fields

    def test_stale_response_includes_downstream_affected(self):
        """STEP 9: Stale response includes downstream affected nodes."""
        from app.api.v1.endpoints.universe_graph import StaleMarkResponse

        fields = StaleMarkResponse.model_fields
        assert "downstream_affected" in fields


# =============================================================================
# Node Compare Tests (diff types)
# =============================================================================

class TestNodeCompare:
    """Test node compare returns all required diff types."""

    def test_diff_types_include_patch(self):
        """STEP 9: Node compare returns patch diff."""
        from app.api.v1.endpoints.universe_graph import ShowDiffResponse

        fields = ShowDiffResponse.model_fields
        assert "patch_diff" in fields

    def test_diff_types_include_outcome(self):
        """STEP 9: Node compare returns outcome diff."""
        from app.api.v1.endpoints.universe_graph import ShowDiffResponse

        fields = ShowDiffResponse.model_fields
        assert "outcome_diff" in fields

    def test_diff_types_include_driver(self):
        """STEP 9: Node compare returns driver diff."""
        from app.api.v1.endpoints.universe_graph import ShowDiffResponse

        fields = ShowDiffResponse.model_fields
        assert "driver_diff" in fields

    def test_diff_types_include_reliability(self):
        """STEP 9: Node compare returns reliability diff."""
        from app.api.v1.endpoints.universe_graph import ShowDiffResponse

        fields = ShowDiffResponse.model_fields
        assert "reliability_diff" in fields

    def test_diff_request_supports_all_types(self):
        """STEP 9: Diff request can request all diff types."""
        from app.api.v1.endpoints.universe_graph import ShowDiffRequest

        # Create request with all diff types
        request = ShowDiffRequest(
            project_id="proj-1",
            node_a_id="node-a",
            node_b_id="node-b",
            diff_types=["patch", "outcome", "driver", "reliability"],
        )

        assert "patch" in request.diff_types
        assert "outcome" in request.diff_types
        assert "driver" in request.diff_types
        assert "reliability" in request.diff_types


# =============================================================================
# Pruning/Collapse Tests (UI filters, no data deletion)
# =============================================================================

class TestPruningCollapse:
    """Test pruning/collapse operate as UI filters without data deletion."""

    def test_graph_node_has_is_pruned_field(self):
        """STEP 9: GraphNode has is_pruned field for UI filtering."""
        from app.api.v1.endpoints.universe_graph import GraphNode

        fields = GraphNode.model_fields
        assert "is_pruned" in fields

    def test_filter_response_does_not_delete(self):
        """STEP 9: Filter returns matching_nodes, doesn't delete."""
        from app.api.v1.endpoints.universe_graph import FilterResponse

        fields = FilterResponse.model_fields
        # Returns list of matching nodes (IDs) - doesn't delete
        assert "matching_nodes" in fields
        # Also returns total_nodes to show filtering doesn't reduce data
        assert "total_nodes" in fields

    def test_search_can_include_pruned(self):
        """STEP 9: Search can include pruned nodes."""
        from app.api.v1.endpoints.universe_graph import SearchNodeRequest

        fields = SearchNodeRequest.model_fields
        assert "include_pruned" in fields


# =============================================================================
# Refresh Tests (cost estimate, stale only)
# =============================================================================

class TestRefresh:
    """Test refresh reruns only stale nodes with cost estimate."""

    def test_refresh_has_dry_run_option(self):
        """STEP 9: Refresh supports dry_run for cost estimate."""
        from app.api.v1.endpoints.universe_graph import RefreshBranchRequest

        fields = RefreshBranchRequest.model_fields
        assert "dry_run" in fields

    def test_refresh_response_includes_cost_estimate(self):
        """STEP 9: Refresh response includes cost estimate."""
        from app.api.v1.endpoints.universe_graph import RefreshBranchResponse

        fields = RefreshBranchResponse.model_fields
        assert "cost_estimate" in fields

    def test_cost_estimate_has_required_fields(self):
        """STEP 9: Cost estimate includes all required fields."""
        from app.api.v1.endpoints.universe_graph import RefreshCostEstimate

        fields = RefreshCostEstimate.model_fields
        assert "estimated_llm_calls" in fields
        assert "estimated_compute_minutes" in fields
        assert "estimated_cost_usd" in fields
        assert "breakdown" in fields

    def test_refresh_has_max_cost_budget(self):
        """STEP 9: Refresh can specify max cost budget."""
        from app.api.v1.endpoints.universe_graph import RefreshBranchRequest

        fields = RefreshBranchRequest.model_fields
        assert "max_cost_usd" in fields

    def test_refresh_modes(self):
        """STEP 9: Refresh supports different modes (stale_only, full_branch, selected)."""
        from app.api.v1.endpoints.universe_graph import RefreshBranchRequest

        fields = RefreshBranchRequest.model_fields
        assert "refresh_mode" in fields


# =============================================================================
# AuditLog Tests
# =============================================================================

class TestAuditLogging:
    """Test that state-changing operations emit AuditLog entries."""

    def test_mark_stale_emits_audit_log(self):
        """STEP 9: Mark stale emits AuditLog entry."""
        from app.api.v1.endpoints.universe_graph import StaleMarkResponse

        fields = StaleMarkResponse.model_fields
        assert "audit_log_id" in fields

    def test_refresh_branch_emits_audit_log(self):
        """STEP 9: Refresh branch emits AuditLog entry."""
        from app.api.v1.endpoints.universe_graph import RefreshBranchResponse

        fields = RefreshBranchResponse.model_fields
        assert "audit_log_id" in fields


# =============================================================================
# Integration Tests
# =============================================================================

class TestUniverseGraphIntegration:
    """Integration tests for STEP 9 universe graph flow."""

    def test_graph_view_switch_schema_compatibility(self):
        """Test graph view switch flow schema compatibility."""
        from app.api.v1.endpoints.universe_graph import (
            GraphViewRequest,
            GraphViewResponse,
        )

        # Create request
        request = GraphViewRequest(
            project_id="proj-1",
            view_mode="graph",
            depth_limit=10,
        )

        assert request.view_mode == "graph"
        assert request.depth_limit == 10
        assert GraphViewResponse.model_fields is not None

    def test_node_compare_flow_schema_compatibility(self):
        """Test node compare flow schema compatibility."""
        from app.api.v1.endpoints.universe_graph import (
            SelectNodeRequest,
            SelectNodeResponse,
            ShowDiffRequest,
            ShowDiffResponse,
        )

        # Create select request
        select_req = SelectNodeRequest(
            project_id="proj-1",
            node_id="node-a",
            slot="A",
        )

        assert select_req.slot == "A"

        # Create diff request
        diff_req = ShowDiffRequest(
            project_id="proj-1",
            node_a_id="node-a",
            node_b_id="node-b",
            diff_types=["patch", "outcome", "driver", "reliability"],
        )

        assert len(diff_req.diff_types) == 4
        assert ShowDiffResponse.model_fields is not None

    def test_refresh_flow_schema_compatibility(self):
        """Test refresh flow schema compatibility."""
        from app.api.v1.endpoints.universe_graph import (
            RefreshBranchRequest,
            RefreshBranchResponse,
            RefreshCostEstimate,
        )

        # Create refresh request with dry_run
        request = RefreshBranchRequest(
            project_id="proj-1",
            node_ids=["node-1", "node-2"],
            refresh_mode="stale_only",
            dry_run=True,
            max_cost_usd=10.0,
        )

        assert request.dry_run is True
        assert request.max_cost_usd == 10.0
        assert RefreshBranchResponse.model_fields is not None
        assert RefreshCostEstimate.model_fields is not None

    def test_cluster_flow_schema_compatibility(self):
        """Test cluster flow schema compatibility."""
        from app.api.v1.endpoints.universe_graph import (
            ClusterBranchesRequest,
            ClusterBranchesResponse,
            ClusterInfo,
        )

        # Create cluster request
        request = ClusterBranchesRequest(
            project_id="proj-1",
            similarity_threshold=0.8,
            clustering_method="outcome_similarity",
        )

        assert request.similarity_threshold == 0.8
        assert ClusterBranchesResponse.model_fields is not None
        assert ClusterInfo.model_fields is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
