"""
Persona API Endpoints
Comprehensive endpoints for persona management, generation, upload, and AI research.
"""

import random
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.persona import (
    PersonaTemplate,
    PersonaRecord,
    PersonaUpload,
    AIResearchJob,
)
from app.models.world import WorldState, WorldStatus
from app.services.advanced_persona import (
    AdvancedPersonaGenerator,
    PersonaGenerationConfig,
    PersonaService,
)
from app.services.persona_upload import (
    PersonaUploadService,
    PersonaFileParser,
    ColumnMapping,
    FileAnalysis,
    UploadResult,
    generate_upload_template,
)
from app.services.ai_research import (
    AIResearchService,
    ResearchConfig,
    ResearchResult,
)
from app.services.regional_data import MultiRegionDataService

router = APIRouter()


# ============= Request/Response Models =============

class PersonaTemplateCreate(BaseModel):
    """Create a persona template."""
    name: str
    description: Optional[str] = None
    region: str
    country: Optional[str] = None
    sub_region: Optional[str] = None
    industry: Optional[str] = None
    topic: Optional[str] = None
    keywords: Optional[list[str]] = None
    source_type: str = "ai_generated"


class PersonaTemplateUpdate(BaseModel):
    """Update a persona template."""
    name: Optional[str] = None
    description: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    sub_region: Optional[str] = None
    industry: Optional[str] = None
    topic: Optional[str] = None
    keywords: Optional[list[str]] = None
    is_active: Optional[bool] = None
    is_public: Optional[bool] = None


class PersonaTemplateResponse(BaseModel):
    """Persona template response."""
    id: UUID
    name: str
    description: Optional[str]
    region: str
    country: Optional[str]
    sub_region: Optional[str]
    industry: Optional[str]
    topic: Optional[str]
    keywords: Optional[list[str]]
    source_type: str
    data_completeness: float
    confidence_score: float
    is_active: bool
    is_public: bool
    persona_count: int = 0
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class PersonaRecordResponse(BaseModel):
    """Persona record response."""
    id: UUID
    demographics: dict[str, Any]
    professional: dict[str, Any]
    psychographics: dict[str, Any]
    behavioral: dict[str, Any]
    interests: dict[str, Any]
    topic_knowledge: Optional[dict[str, Any]]
    cultural_context: Optional[dict[str, Any]]
    source_type: str
    confidence_score: float
    full_prompt: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


class GeneratePersonasRequest(BaseModel):
    """Request to generate personas."""
    template_id: Optional[UUID] = None
    region: str
    country: Optional[str] = None
    sub_region: Optional[str] = None
    topic: Optional[str] = None
    industry: Optional[str] = None
    keywords: Optional[list[str]] = None
    count: int = Field(default=100, ge=1, le=1000)
    include_psychographics: bool = True
    include_behavioral: bool = True
    include_cultural: bool = True
    include_topic_knowledge: bool = True


class GeneratePersonasResponse(BaseModel):
    """Response from persona generation."""
    count: int
    template_id: Optional[UUID]
    sample_personas: list[dict[str, Any]]
    generation_config: dict[str, Any]


class UploadAnalysisResponse(BaseModel):
    """Response from file analysis."""
    file_name: str
    row_count: int
    column_count: int
    columns: list[dict[str, Any]]
    suggested_mappings: dict[str, str]


class AIResearchRequest(BaseModel):
    """Request for AI research."""
    topic: str
    region: str
    country: Optional[str] = None
    industry: Optional[str] = None
    keywords: Optional[list[str]] = Field(default_factory=list)
    research_depth: str = Field(default="standard", pattern="^(quick|standard|comprehensive)$")
    target_persona_count: int = Field(default=100, ge=10, le=1000)


class AIResearchJobResponse(BaseModel):
    """AI research job response."""
    id: UUID
    topic: str
    region: str
    country: Optional[str]
    industry: Optional[str]
    status: str
    progress: int
    insights: Optional[dict[str, Any]]
    personas_generated: int
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]

    class Config:
        from_attributes = True


class RegionInfo(BaseModel):
    """Information about a supported region."""
    code: str
    name: str
    countries: list[str]
    data_source: str


# ============= Template Endpoints =============

@router.post("/templates", response_model=PersonaTemplateResponse)
async def create_template(
    data: PersonaTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new persona template."""
    config = PersonaGenerationConfig(
        region=data.region,
        country=data.country,
        sub_region=data.sub_region,
        topic=data.topic,
        industry=data.industry,
        keywords=data.keywords or [],
        source_type=data.source_type,
    )

    service = PersonaService(db)
    template = await service.create_template(
        user_id=current_user.id,
        config=config,
        name=data.name,
        description=data.description,
    )

    return PersonaTemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        region=template.region,
        country=template.country,
        sub_region=template.sub_region,
        industry=template.industry,
        topic=template.topic,
        keywords=template.keywords,
        source_type=template.source_type,
        data_completeness=template.data_completeness,
        confidence_score=template.confidence_score,
        is_active=template.is_active,
        is_public=template.is_public,
        persona_count=0,
        created_at=template.created_at.isoformat(),
        updated_at=template.updated_at.isoformat(),
    )


@router.get("/templates", response_model=list[PersonaTemplateResponse])
async def list_templates(
    skip: int = 0,
    limit: int = 20,
    region: Optional[str] = None,
    source_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List persona templates for the current user."""
    query = select(PersonaTemplate).where(PersonaTemplate.user_id == current_user.id)

    if region:
        query = query.where(PersonaTemplate.region == region)
    if source_type:
        query = query.where(PersonaTemplate.source_type == source_type)

    query = query.order_by(PersonaTemplate.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    templates = result.scalars().all()

    # Get persona counts
    responses = []
    for template in templates:
        count_result = await db.execute(
            select(func.count(PersonaRecord.id))
            .where(PersonaRecord.template_id == template.id)
        )
        persona_count = count_result.scalar() or 0

        responses.append(PersonaTemplateResponse(
            id=template.id,
            name=template.name,
            description=template.description,
            region=template.region,
            country=template.country,
            sub_region=template.sub_region,
            industry=template.industry,
            topic=template.topic,
            keywords=template.keywords,
            source_type=template.source_type,
            data_completeness=template.data_completeness,
            confidence_score=template.confidence_score,
            is_active=template.is_active,
            is_public=template.is_public,
            persona_count=persona_count,
            created_at=template.created_at.isoformat(),
            updated_at=template.updated_at.isoformat(),
        ))

    return responses


@router.get("/templates/{template_id}", response_model=PersonaTemplateResponse)
async def get_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific persona template."""
    result = await db.execute(
        select(PersonaTemplate).where(
            PersonaTemplate.id == template_id,
            PersonaTemplate.user_id == current_user.id,
        )
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    count_result = await db.execute(
        select(func.count(PersonaRecord.id))
        .where(PersonaRecord.template_id == template.id)
    )
    persona_count = count_result.scalar() or 0

    return PersonaTemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        region=template.region,
        country=template.country,
        sub_region=template.sub_region,
        industry=template.industry,
        topic=template.topic,
        keywords=template.keywords,
        source_type=template.source_type,
        data_completeness=template.data_completeness,
        confidence_score=template.confidence_score,
        is_active=template.is_active,
        is_public=template.is_public,
        persona_count=persona_count,
        created_at=template.created_at.isoformat(),
        updated_at=template.updated_at.isoformat(),
    )


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a persona template and all associated personas."""
    result = await db.execute(
        select(PersonaTemplate).where(
            PersonaTemplate.id == template_id,
            PersonaTemplate.user_id == current_user.id,
        )
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    await db.delete(template)
    await db.commit()

    return {"message": "Template deleted successfully"}


# ============= Persona Generation Endpoints =============

@router.post("/generate", response_model=GeneratePersonasResponse)
async def generate_personas(
    request: GeneratePersonasRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate personas based on configuration."""
    config = PersonaGenerationConfig(
        region=request.region,
        country=request.country,
        sub_region=request.sub_region,
        topic=request.topic,
        industry=request.industry,
        keywords=request.keywords or [],
        count=request.count,
        source_type="ai_generated",
        include_psychographics=request.include_psychographics,
        include_behavioral=request.include_behavioral,
        include_cultural=request.include_cultural,
        include_topic_knowledge=request.include_topic_knowledge,
    )

    # Generate personas
    generator = AdvancedPersonaGenerator(config)
    personas = await generator.generate_personas(min(request.count, 5))  # Generate sample first

    # Save to database if template provided
    if request.template_id:
        service = PersonaService(db)
        await service.generate_and_save_personas(
            template_id=request.template_id,
            config=config,
            count=request.count,
        )

        # Auto-create and start Vi World for this template
        try:
            await _auto_create_world(db, request.template_id)
        except Exception as e:
            # Don't fail persona generation if world creation fails
            import structlog
            logger = structlog.get_logger()
            logger.warning("Failed to auto-create world", template_id=str(request.template_id), error=str(e))

    return GeneratePersonasResponse(
        count=request.count,
        template_id=request.template_id,
        sample_personas=[p.model_dump() for p in personas[:5]],
        generation_config=config.model_dump(),
    )


@router.get("/templates/{template_id}/personas", response_model=list[PersonaRecordResponse])
async def list_personas(
    template_id: UUID,
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List personas for a template."""
    # Verify template ownership
    result = await db.execute(
        select(PersonaTemplate).where(
            PersonaTemplate.id == template_id,
            PersonaTemplate.user_id == current_user.id,
        )
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Get personas
    result = await db.execute(
        select(PersonaRecord)
        .where(PersonaRecord.template_id == template_id)
        .offset(skip)
        .limit(limit)
    )
    personas = result.scalars().all()

    return [
        PersonaRecordResponse(
            id=p.id,
            demographics=p.demographics,
            professional=p.professional,
            psychographics=p.psychographics,
            behavioral=p.behavioral,
            interests=p.interests,
            topic_knowledge=p.topic_knowledge,
            cultural_context=p.cultural_context,
            source_type=p.source_type,
            confidence_score=p.confidence_score,
            full_prompt=p.full_prompt,
            created_at=p.created_at.isoformat(),
        )
        for p in personas
    ]


# ============= Upload Endpoints =============

@router.post("/upload/analyze", response_model=UploadAnalysisResponse)
async def analyze_upload(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Analyze an uploaded file and suggest column mappings."""
    content = await file.read()

    try:
        analysis = PersonaFileParser.analyze_file(content, file.filename)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to analyze file: {str(e)}")

    return UploadAnalysisResponse(
        file_name=analysis.file_name,
        row_count=analysis.row_count,
        column_count=analysis.column_count,
        columns=[c.model_dump() for c in analysis.columns],
        suggested_mappings=analysis.suggested_mappings,
    )


@router.post("/upload/process")
async def process_upload(
    file: UploadFile = File(...),
    mapping: str = "",  # JSON string of column mappings
    template_id: Optional[UUID] = None,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Process an uploaded file and create persona records."""
    content = await file.read()

    # Parse mapping
    try:
        mapping_dict = {} if not mapping else __import__("json").loads(mapping)
        column_mapping = ColumnMapping(**mapping_dict)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid column mapping: {str(e)}")

    service = PersonaUploadService(db)

    # Create upload record
    upload = await service.create_upload_record(
        user_id=current_user.id,
        file_name=file.filename,
        file_type=file.filename.split(".")[-1],
        file_size=len(content),
        template_id=template_id,
    )

    # Process upload
    try:
        result = await service.process_upload(
            upload_id=upload.id,
            file_content=content,
            file_name=file.filename,
            mapping=column_mapping,
            template_id=template_id,
        )
        return result.model_dump()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Upload processing failed: {str(e)}")


@router.get("/upload/template")
async def get_upload_template(
    current_user: User = Depends(get_current_user),
):
    """Download a CSV template for persona uploads."""
    from fastapi.responses import StreamingResponse
    import io

    template_content = generate_upload_template()

    return StreamingResponse(
        io.BytesIO(template_content),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=persona_upload_template.csv"}
    )


@router.get("/uploads", response_model=list[dict])
async def list_uploads(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List upload history for the current user."""
    service = PersonaUploadService(db)
    uploads = await service.list_uploads(current_user.id, limit, skip)

    return [
        {
            "id": u.id,
            "file_name": u.file_name,
            "file_type": u.file_type,
            "file_size": u.file_size,
            "status": u.status,
            "records_total": u.records_total,
            "records_processed": u.records_processed,
            "records_failed": u.records_failed,
            "created_at": u.created_at.isoformat(),
            "completed_at": u.completed_at.isoformat() if u.completed_at else None,
        }
        for u in uploads
    ]


# ============= AI Research Endpoints =============

@router.post("/research", response_model=AIResearchJobResponse)
async def start_research(
    request: AIResearchRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start an AI research job to discover audience insights and generate personas."""
    config = ResearchConfig(
        topic=request.topic,
        region=request.region,
        country=request.country,
        industry=request.industry,
        keywords=request.keywords,
        research_depth=request.research_depth,
        target_persona_count=request.target_persona_count,
    )

    service = AIResearchService(db)
    job = await service.create_research_job(
        user_id=current_user.id,
        config=config,
    )

    # Run research in background
    background_tasks.add_task(service.run_research, job.id)

    return AIResearchJobResponse(
        id=job.id,
        topic=job.topic,
        region=job.region,
        country=job.country,
        industry=job.industry,
        status=job.status,
        progress=job.progress,
        insights=job.insights,
        personas_generated=job.personas_generated,
        created_at=job.created_at.isoformat(),
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
    )


@router.get("/research/{job_id}", response_model=AIResearchJobResponse)
async def get_research_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the status and results of a research job."""
    result = await db.execute(
        select(AIResearchJob).where(
            AIResearchJob.id == job_id,
            AIResearchJob.user_id == current_user.id,
        )
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Research job not found")

    return AIResearchJobResponse(
        id=job.id,
        topic=job.topic,
        region=job.region,
        country=job.country,
        industry=job.industry,
        status=job.status,
        progress=job.progress,
        insights=job.insights,
        personas_generated=job.personas_generated,
        created_at=job.created_at.isoformat(),
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
    )


@router.get("/research", response_model=list[AIResearchJobResponse])
async def list_research_jobs(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List research jobs for the current user."""
    service = AIResearchService(db)
    jobs = await service.list_jobs(current_user.id, limit, skip)

    return [
        AIResearchJobResponse(
            id=job.id,
            topic=job.topic,
            region=job.region,
            country=job.country,
            industry=job.industry,
            status=job.status,
            progress=job.progress,
            insights=job.insights,
            personas_generated=job.personas_generated,
            created_at=job.created_at.isoformat(),
            started_at=job.started_at.isoformat() if job.started_at else None,
            completed_at=job.completed_at.isoformat() if job.completed_at else None,
        )
        for job in jobs
    ]


# ============= Region Info Endpoints =============

@router.get("/regions", response_model=list[RegionInfo])
async def list_supported_regions(
    current_user: User = Depends(get_current_user),
):
    """List all supported regions and their data sources."""
    service = MultiRegionDataService()

    regions = [
        RegionInfo(
            code="us",
            name="United States",
            countries=service.list_supported_countries("us"),
            data_source="US Census Bureau ACS 5-Year",
        ),
        RegionInfo(
            code="europe",
            name="Europe",
            countries=service.list_supported_countries("europe"),
            data_source="Eurostat",
        ),
        RegionInfo(
            code="southeast_asia",
            name="Southeast Asia",
            countries=service.list_supported_countries("southeast_asia"),
            data_source="ASEAN Statistics & National Census Data",
        ),
        RegionInfo(
            code="china",
            name="China",
            countries=service.list_supported_countries("china"),
            data_source="China National Bureau of Statistics",
        ),
    ]

    return regions


@router.get("/regions/{region_code}/demographics")
async def get_region_demographics(
    region_code: str,
    country: Optional[str] = None,
    sub_region: Optional[str] = None,
    year: Optional[int] = None,
    current_user: User = Depends(get_current_user),
):
    """Get demographic data for a specific region."""
    service = MultiRegionDataService()

    try:
        demographics = await service.get_demographics(
            region=region_code,
            country=country,
            sub_region=sub_region,
            year=year,
        )
        return demographics.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============= STEP 3: Persona Validation Endpoints =============

class PersonaValidationResponse(BaseModel):
    """STEP 3: Persona validation report response."""
    id: str
    tenant_id: str
    template_id: Optional[str] = None
    status: str
    overall_score: float
    coverage_gaps: dict
    duplication_analysis: dict
    bias_risk: dict
    uncertainty_warnings: dict
    statistics: dict
    recommendations: list
    confidence_impact: float
    created_at: str


@router.post("/validate/{project_id}", response_model=PersonaValidationResponse)
async def validate_persona_set(
    project_id: UUID,
    template_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    STEP 3: Validate a persona set and generate a quality report.

    This endpoint analyzes all active personas in a project and generates
    a comprehensive validation report including:
    - Coverage gaps (missing demographic segments)
    - Duplication analysis (overlapping personas)
    - Bias risk (over/under-representation)
    - Uncertainty warnings (data quality issues)
    - Recommendations for improvement

    The report is stored in the database and can be linked to a PersonaSnapshot
    for confidence calculations in simulation outcomes.

    Args:
        project_id: The project UUID to validate personas for
        template_id: Optional template UUID for filtering

    Returns:
        PersonaValidationResponse with full analysis results
    """
    from app.services.persona_validation import get_persona_validation_service

    try:
        service = await get_persona_validation_service(db)
        report = await service.validate_persona_set(
            tenant_id=str(current_user.tenant_id),
            project_id=str(project_id),
            template_id=str(template_id) if template_id else None,
        )
        await db.commit()
        return PersonaValidationResponse(**report)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@router.get("/validation-reports/{project_id}", response_model=list[PersonaValidationResponse])
async def list_validation_reports(
    project_id: UUID,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    STEP 3: List validation reports for a project.

    Returns recent validation reports for the specified project.
    """
    from sqlalchemy import text

    query = text("""
        SELECT id, tenant_id, template_id, status, overall_score,
               coverage_gaps, duplication_analysis, bias_risk,
               uncertainty_warnings, statistics, recommendations,
               confidence_impact, created_at
        FROM persona_validation_reports
        WHERE tenant_id = :tenant_id
        ORDER BY created_at DESC
        LIMIT :limit
    """)

    result = await db.execute(query, {
        "tenant_id": str(current_user.tenant_id),
        "limit": limit,
    })
    rows = result.fetchall()

    reports = []
    for row in rows:
        reports.append(PersonaValidationResponse(
            id=str(row.id),
            tenant_id=str(row.tenant_id),
            template_id=str(row.template_id) if row.template_id else None,
            status=row.status,
            overall_score=row.overall_score,
            coverage_gaps=row.coverage_gaps if isinstance(row.coverage_gaps, dict) else {},
            duplication_analysis=row.duplication_analysis if isinstance(row.duplication_analysis, dict) else {},
            bias_risk=row.bias_risk if isinstance(row.bias_risk, dict) else {},
            uncertainty_warnings=row.uncertainty_warnings if isinstance(row.uncertainty_warnings, dict) else {},
            statistics=row.statistics if isinstance(row.statistics, dict) else {},
            recommendations=row.recommendations if isinstance(row.recommendations, list) else [],
            confidence_impact=row.confidence_impact,
            created_at=row.created_at.isoformat() if row.created_at else "",
        ))

    return reports


# =============================================================================
# STEP 3: Persona Snapshot Endpoints (Immutable Snapshot Management)
# =============================================================================

class PersonaSnapshotCreate(BaseModel):
    """STEP 3: Request to create a persona snapshot."""
    project_id: UUID
    template_id: Optional[UUID] = None
    name: str
    description: Optional[str] = None


class PersonaSnapshotResponse(BaseModel):
    """STEP 3: Persona snapshot response."""
    id: str
    tenant_id: str
    project_id: str
    source_template_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    total_personas: int
    segment_summary: dict
    data_hash: str
    confidence_score: float
    data_completeness: float
    is_locked: bool
    validation_report_id: Optional[str] = None
    created_at: str


class SnapshotCompareResponse(BaseModel):
    """STEP 3: Snapshot comparison response."""
    snapshot_a: dict
    snapshot_b: dict
    differences: dict
    similarity_score: float


@router.post("/snapshots", response_model=PersonaSnapshotResponse)
async def create_persona_snapshot(
    request: PersonaSnapshotCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    STEP 3: Save as Snapshot - Create an immutable persona snapshot.

    This endpoint creates a frozen copy of the current persona set for use
    in simulation runs. Once created, the snapshot is immutable and will
    be referenced by RunSpec.personas_snapshot_id.

    Args:
        request: Snapshot creation parameters

    Returns:
        PersonaSnapshotResponse with the created snapshot details
    """
    import hashlib
    import json
    from uuid import uuid4
    from app.models.persona import PersonaSnapshot

    # Get personas from template or project
    if request.template_id:
        result = await db.execute(
            select(PersonaRecord)
            .where(PersonaRecord.template_id == request.template_id)
        )
    else:
        # Get all personas for the project via templates
        result = await db.execute(
            select(PersonaRecord)
            .join(PersonaTemplate)
            .where(PersonaTemplate.user_id == current_user.id)
            .limit(1000)
        )

    personas = result.scalars().all()

    if not personas:
        raise HTTPException(status_code=400, detail="No personas found to snapshot")

    # Build personas_data for immutable storage
    personas_data = []
    for p in personas:
        personas_data.append({
            "id": str(p.id),
            "demographics": p.demographics,
            "professional": p.professional,
            "psychographics": p.psychographics,
            "behavioral": p.behavioral,
            "interests": p.interests,
            "topic_knowledge": p.topic_knowledge,
            "cultural_context": p.cultural_context,
            "source_type": p.source_type,
            "confidence_score": p.confidence_score,
        })

    # Compute segment summary
    segment_summary = _compute_segment_summary(personas_data)

    # Compute data hash for integrity verification
    data_hash = hashlib.sha256(
        json.dumps(personas_data, sort_keys=True, default=str).encode()
    ).hexdigest()

    # Create snapshot
    snapshot = PersonaSnapshot(
        id=uuid4(),
        tenant_id=current_user.tenant_id,
        project_id=request.project_id,
        source_template_id=request.template_id,
        name=request.name,
        description=request.description,
        total_personas=len(personas_data),
        segment_summary=segment_summary,
        personas_data=personas_data,
        data_hash=data_hash,
        confidence_score=sum(p.get("confidence_score", 0.8) for p in personas_data) / len(personas_data),
        data_completeness=1.0,
        is_locked=True,  # Snapshots are immutable by default
    )

    db.add(snapshot)
    await db.commit()
    await db.refresh(snapshot)

    return PersonaSnapshotResponse(
        id=str(snapshot.id),
        tenant_id=str(snapshot.tenant_id),
        project_id=str(snapshot.project_id),
        source_template_id=str(snapshot.source_template_id) if snapshot.source_template_id else None,
        name=snapshot.name,
        description=snapshot.description,
        total_personas=snapshot.total_personas,
        segment_summary=snapshot.segment_summary,
        data_hash=snapshot.data_hash,
        confidence_score=snapshot.confidence_score,
        data_completeness=snapshot.data_completeness,
        is_locked=snapshot.is_locked,
        validation_report_id=str(snapshot.validation_report_id) if snapshot.validation_report_id else None,
        created_at=snapshot.created_at.isoformat(),
    )


@router.get("/snapshots", response_model=list[PersonaSnapshotResponse])
async def list_persona_snapshots(
    project_id: UUID,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    STEP 3: List all persona snapshots for a project.
    """
    from app.models.persona import PersonaSnapshot

    result = await db.execute(
        select(PersonaSnapshot)
        .where(
            PersonaSnapshot.tenant_id == current_user.tenant_id,
            PersonaSnapshot.project_id == project_id,
        )
        .order_by(PersonaSnapshot.created_at.desc())
        .limit(limit)
    )
    snapshots = result.scalars().all()

    return [
        PersonaSnapshotResponse(
            id=str(s.id),
            tenant_id=str(s.tenant_id),
            project_id=str(s.project_id),
            source_template_id=str(s.source_template_id) if s.source_template_id else None,
            name=s.name,
            description=s.description,
            total_personas=s.total_personas,
            segment_summary=s.segment_summary,
            data_hash=s.data_hash,
            confidence_score=s.confidence_score,
            data_completeness=s.data_completeness,
            is_locked=s.is_locked,
            validation_report_id=str(s.validation_report_id) if s.validation_report_id else None,
            created_at=s.created_at.isoformat(),
        )
        for s in snapshots
    ]


@router.get("/snapshots/{snapshot_id}", response_model=PersonaSnapshotResponse)
async def get_persona_snapshot(
    snapshot_id: UUID,
    include_data: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    STEP 3: View Snapshot JSON - Get detailed snapshot information.

    Args:
        snapshot_id: The snapshot UUID
        include_data: If True, includes full personas_data (can be large)

    Returns:
        PersonaSnapshotResponse with snapshot details
    """
    from app.models.persona import PersonaSnapshot

    result = await db.execute(
        select(PersonaSnapshot)
        .where(
            PersonaSnapshot.id == snapshot_id,
            PersonaSnapshot.tenant_id == current_user.tenant_id,
        )
    )
    snapshot = result.scalar_one_or_none()

    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    response = PersonaSnapshotResponse(
        id=str(snapshot.id),
        tenant_id=str(snapshot.tenant_id),
        project_id=str(snapshot.project_id),
        source_template_id=str(snapshot.source_template_id) if snapshot.source_template_id else None,
        name=snapshot.name,
        description=snapshot.description,
        total_personas=snapshot.total_personas,
        segment_summary=snapshot.segment_summary,
        data_hash=snapshot.data_hash,
        confidence_score=snapshot.confidence_score,
        data_completeness=snapshot.data_completeness,
        is_locked=snapshot.is_locked,
        validation_report_id=str(snapshot.validation_report_id) if snapshot.validation_report_id else None,
        created_at=snapshot.created_at.isoformat(),
    )

    return response


@router.get("/snapshots/{snapshot_id}/data")
async def get_snapshot_data(
    snapshot_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    STEP 3: Get full personas data from a snapshot.
    """
    from app.models.persona import PersonaSnapshot

    result = await db.execute(
        select(PersonaSnapshot)
        .where(
            PersonaSnapshot.id == snapshot_id,
            PersonaSnapshot.tenant_id == current_user.tenant_id,
        )
    )
    snapshot = result.scalar_one_or_none()

    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    return {
        "snapshot_id": str(snapshot.id),
        "total_personas": snapshot.total_personas,
        "data_hash": snapshot.data_hash,
        "personas_data": snapshot.personas_data,
    }


@router.get("/snapshots/compare")
async def compare_snapshots(
    snapshot_a_id: UUID,
    snapshot_b_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    STEP 3: Compare Snapshots - Compare two persona snapshots.

    Analyzes differences in demographics, distributions, and segment composition.

    Returns:
        Comparison results with similarity score and detailed differences
    """
    from app.models.persona import PersonaSnapshot

    # Get both snapshots
    result_a = await db.execute(
        select(PersonaSnapshot)
        .where(
            PersonaSnapshot.id == snapshot_a_id,
            PersonaSnapshot.tenant_id == current_user.tenant_id,
        )
    )
    snapshot_a = result_a.scalar_one_or_none()

    result_b = await db.execute(
        select(PersonaSnapshot)
        .where(
            PersonaSnapshot.id == snapshot_b_id,
            PersonaSnapshot.tenant_id == current_user.tenant_id,
        )
    )
    snapshot_b = result_b.scalar_one_or_none()

    if not snapshot_a or not snapshot_b:
        raise HTTPException(status_code=404, detail="One or both snapshots not found")

    # Compare segment summaries
    differences = _compare_segment_summaries(
        snapshot_a.segment_summary,
        snapshot_b.segment_summary
    )

    # Calculate similarity score
    similarity_score = _calculate_similarity_score(snapshot_a, snapshot_b)

    return {
        "snapshot_a": {
            "id": str(snapshot_a.id),
            "name": snapshot_a.name,
            "total_personas": snapshot_a.total_personas,
            "segment_summary": snapshot_a.segment_summary,
            "created_at": snapshot_a.created_at.isoformat(),
        },
        "snapshot_b": {
            "id": str(snapshot_b.id),
            "name": snapshot_b.name,
            "total_personas": snapshot_b.total_personas,
            "segment_summary": snapshot_b.segment_summary,
            "created_at": snapshot_b.created_at.isoformat(),
        },
        "differences": differences,
        "similarity_score": similarity_score,
    }


@router.post("/snapshots/{snapshot_id}/lock")
async def lock_snapshot(
    snapshot_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    STEP 3: Lock Snapshot - Mark a snapshot as permanently locked.

    Once locked, a snapshot cannot be modified or deleted.
    This is typically automatic but can be explicitly enforced.

    Returns:
        Success message with lock status
    """
    from app.models.persona import PersonaSnapshot

    result = await db.execute(
        select(PersonaSnapshot)
        .where(
            PersonaSnapshot.id == snapshot_id,
            PersonaSnapshot.tenant_id == current_user.tenant_id,
        )
    )
    snapshot = result.scalar_one_or_none()

    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    if snapshot.is_locked:
        return {
            "message": "Snapshot is already locked",
            "snapshot_id": str(snapshot.id),
            "is_locked": True,
        }

    snapshot.is_locked = True
    await db.commit()

    return {
        "message": "Snapshot locked successfully",
        "snapshot_id": str(snapshot.id),
        "is_locked": True,
    }


@router.get("/snapshots/{snapshot_id}/export")
async def export_snapshot(
    snapshot_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    STEP 3: Export Snapshot - Download snapshot as JSON file.

    Returns the complete snapshot data as a downloadable JSON file.
    """
    from fastapi.responses import Response
    import json
    from app.models.persona import PersonaSnapshot

    result = await db.execute(
        select(PersonaSnapshot)
        .where(
            PersonaSnapshot.id == snapshot_id,
            PersonaSnapshot.tenant_id == current_user.tenant_id,
        )
    )
    snapshot = result.scalar_one_or_none()

    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    export_data = {
        "snapshot_id": str(snapshot.id),
        "name": snapshot.name,
        "description": snapshot.description,
        "total_personas": snapshot.total_personas,
        "segment_summary": snapshot.segment_summary,
        "data_hash": snapshot.data_hash,
        "confidence_score": snapshot.confidence_score,
        "is_locked": snapshot.is_locked,
        "created_at": snapshot.created_at.isoformat(),
        "personas_data": snapshot.personas_data,
    }

    json_content = json.dumps(export_data, indent=2, default=str)
    safe_name = snapshot.name.replace(" ", "_").replace("/", "-")[:50]
    filename = f"persona_snapshot_{safe_name}_{str(snapshot_id)[:8]}.json"

    return Response(
        content=json_content,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Snapshot-Id": str(snapshot_id),
            "X-Snapshot-Hash": snapshot.data_hash,
        },
    )


@router.post("/snapshots/{snapshot_id}/set-default")
async def set_default_snapshot(
    snapshot_id: UUID,
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    STEP 3: Set as Default Snapshot - Mark a snapshot as the default for a project.

    The default snapshot will be automatically used when creating new runs
    unless a specific snapshot is specified.
    """
    from app.models.persona import PersonaSnapshot
    from app.models.project_spec import ProjectSpec

    # Verify snapshot exists and belongs to user
    result = await db.execute(
        select(PersonaSnapshot)
        .where(
            PersonaSnapshot.id == snapshot_id,
            PersonaSnapshot.tenant_id == current_user.tenant_id,
        )
    )
    snapshot = result.scalar_one_or_none()

    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    # Update project's default snapshot
    project_result = await db.execute(
        select(ProjectSpec)
        .where(
            ProjectSpec.id == project_id,
            ProjectSpec.tenant_id == current_user.tenant_id,
        )
    )
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Store default snapshot in project's extra_config
    if not project.extra_config:
        project.extra_config = {}
    project.extra_config["default_persona_snapshot_id"] = str(snapshot_id)
    project.updated_at = datetime.utcnow()

    await db.commit()

    return {
        "message": "Default snapshot set successfully",
        "project_id": str(project_id),
        "default_snapshot_id": str(snapshot_id),
        "snapshot_name": snapshot.name,
    }


def _compute_segment_summary(personas_data: list) -> dict:
    """Compute segment summary from personas data."""
    if not personas_data:
        return {"segments": [], "demographics_summary": {}}

    # Analyze age distribution
    age_dist = {}
    gender_dist = {}
    region_dist = {}

    for p in personas_data:
        demo = p.get("demographics", {})

        # Age
        age_bracket = demo.get("age_bracket", "Unknown")
        age_dist[age_bracket] = age_dist.get(age_bracket, 0) + 1

        # Gender
        gender = demo.get("gender", "Unknown")
        gender_dist[gender] = gender_dist.get(gender, 0) + 1

        # Region
        region = demo.get("region", "Unknown")
        region_dist[region] = region_dist.get(region, 0) + 1

    total = len(personas_data)

    return {
        "segments": [],  # Can be expanded with clustering
        "demographics_summary": {
            "age_distribution": {k: v / total for k, v in age_dist.items()},
            "gender_distribution": {k: v / total for k, v in gender_dist.items()},
            "region_distribution": {k: v / total for k, v in region_dist.items()},
        },
    }


def _compare_segment_summaries(summary_a: dict, summary_b: dict) -> dict:
    """Compare two segment summaries and return differences."""
    differences = {
        "population_diff": 0,
        "demographic_diffs": {},
    }

    demo_a = summary_a.get("demographics_summary", {})
    demo_b = summary_b.get("demographics_summary", {})

    for key in set(list(demo_a.keys()) + list(demo_b.keys())):
        dist_a = demo_a.get(key, {})
        dist_b = demo_b.get(key, {})

        diffs = {}
        for segment in set(list(dist_a.keys()) + list(dist_b.keys())):
            val_a = dist_a.get(segment, 0)
            val_b = dist_b.get(segment, 0)
            if abs(val_a - val_b) > 0.01:  # 1% threshold
                diffs[segment] = {"a": val_a, "b": val_b, "diff": val_b - val_a}

        if diffs:
            differences["demographic_diffs"][key] = diffs

    return differences


def _calculate_similarity_score(snapshot_a, snapshot_b) -> float:
    """Calculate similarity score between two snapshots."""
    if snapshot_a.data_hash == snapshot_b.data_hash:
        return 1.0

    # Simple similarity based on demographics
    demo_a = snapshot_a.segment_summary.get("demographics_summary", {})
    demo_b = snapshot_b.segment_summary.get("demographics_summary", {})

    if not demo_a or not demo_b:
        return 0.5

    # Calculate cosine similarity on distributions
    scores = []
    for key in demo_a.keys():
        if key in demo_b:
            dist_a = demo_a[key]
            dist_b = demo_b[key]

            all_keys = set(list(dist_a.keys()) + list(dist_b.keys()))
            vec_a = [dist_a.get(k, 0) for k in all_keys]
            vec_b = [dist_b.get(k, 0) for k in all_keys]

            # Simple dot product / magnitude
            dot = sum(a * b for a, b in zip(vec_a, vec_b))
            mag_a = sum(a ** 2 for a in vec_a) ** 0.5
            mag_b = sum(b ** 2 for b in vec_b) ** 0.5

            if mag_a > 0 and mag_b > 0:
                scores.append(dot / (mag_a * mag_b))

    return sum(scores) / len(scores) if scores else 0.5


# ============= Helper Functions =============

async def _auto_create_world(db: AsyncSession, template_id: UUID) -> None:
    """
    Auto-create and start a Vi World for a template.
    Called after personas are generated.
    """
    # Check if world already exists
    result = await db.execute(
        select(WorldState).where(WorldState.template_id == template_id)
    )
    existing_world = result.scalar_one_or_none()

    if existing_world:
        # World already exists, just make sure it's running
        if existing_world.status != WorldStatus.RUNNING.value:
            existing_world.status = WorldStatus.RUNNING.value
            existing_world.started_at = datetime.utcnow()
            existing_world.last_tick_at = datetime.utcnow()
            existing_world.updated_at = datetime.utcnow()
        return

    # Create new world
    seed = random.randint(1, 2**31 - 1)

    world = WorldState(
        template_id=template_id,
        seed=seed,
        world_width=150,
        world_height=114,
        tile_size=16,
        simulation_speed=1.0,
        is_continuous=True,
        status=WorldStatus.INITIALIZING.value,
        npc_states={},
        chat_history=[],
    )

    db.add(world)
    await db.flush()

    # Initialize NPC states from persona records
    result = await db.execute(
        select(PersonaRecord).where(PersonaRecord.template_id == template_id)
    )
    personas = result.scalars().all()

    # Generate random starting positions
    random.seed(seed)

    npc_states = {}
    world_pixel_width = world.world_width * world.tile_size
    world_pixel_height = world.world_height * world.tile_size

    for persona in personas:
        # Generate random position within world bounds
        x = random.randint(50, world_pixel_width - 50)
        y = random.randint(50, world_pixel_height - 50)

        npc_states[str(persona.id)] = {
            "position": {"x": x, "y": y},
            "target_position": None,
            "state": "idle",
            "direction": random.choice(["down", "up", "left", "right"]),
            "speed": random.uniform(35, 55),
            "last_action_time": 0,
            "chat_cooldown": 0,
        }

    world.npc_states = npc_states

    # Start the world
    world.status = WorldStatus.RUNNING.value
    world.started_at = datetime.utcnow()
    world.last_tick_at = datetime.utcnow()

    await db.flush()


# =============================================================================
# PROJECT PERSONAS API - Save AI-Generated Personas to Database
# =============================================================================

class SavePersonasRequest(BaseModel):
    """Request to save AI-generated personas to a project."""
    project_id: UUID
    personas: list[dict[str, Any]] = Field(..., min_length=1)


class SavePersonasResponse(BaseModel):
    """Response from saving personas."""
    saved_count: int
    project_id: str
    persona_ids: list[str]


class ProjectPersonaResponse(BaseModel):
    """Single persona response for project."""
    id: str
    label: str
    source: str
    demographics: dict[str, Any]
    preferences: dict[str, Any]
    perception_weights: dict[str, Any]
    bias_parameters: dict[str, Any]
    action_priors: dict[str, Any]
    uncertainty_score: float
    is_active: bool
    created_at: str


@router.post("/project/{project_id}/save", response_model=SavePersonasResponse)
async def save_project_personas(
    project_id: UUID,
    request: SavePersonasRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Save AI-generated personas to a project.

    This endpoint persists personas generated by the frontend (via OpenRouter)
    to the database. These personas will be used by the simulation engine
    when creating PersonaSnapshots for runs.

    Args:
        project_id: The project UUID to save personas for
        request: List of generated personas with their attributes

    Returns:
        SavePersonasResponse with count and IDs of saved personas
    """
    from uuid import uuid4
    from app.models.persona import Persona
    from app.models.project_spec import ProjectSpec

    # Verify project exists and belongs to user
    project_result = await db.execute(
        select(ProjectSpec)
        .where(
            ProjectSpec.id == project_id,
            ProjectSpec.tenant_id == current_user.id,
        )
    )
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    saved_ids = []

    for persona_data in request.personas:
        # Extract fields from the AI-generated persona
        persona = Persona(
            id=uuid4(),
            tenant_id=current_user.id,
            project_id=project_id,
            label=persona_data.get("name", persona_data.get("label", f"Persona {len(saved_ids) + 1}")),
            source="ai_generated",
            demographics=persona_data.get("demographics", {}),
            preferences=persona_data.get("preferences", persona_data.get("psychographics", {})),
            perception_weights=persona_data.get("perception_weights", {}),
            bias_parameters=persona_data.get("bias_parameters", persona_data.get("biases", {})),
            action_priors=persona_data.get("action_priors", persona_data.get("behavioral", {})),
            uncertainty_score=persona_data.get("uncertainty_score", 0.5),
            is_active=True,
        )

        db.add(persona)
        saved_ids.append(str(persona.id))

    await db.commit()

    return SavePersonasResponse(
        saved_count=len(saved_ids),
        project_id=str(project_id),
        persona_ids=saved_ids,
    )


@router.get("/project/{project_id}", response_model=list[ProjectPersonaResponse])
async def list_project_personas(
    project_id: UUID,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all personas for a project.

    Returns personas from the `personas` table that are linked to this project.
    """
    from app.models.persona import Persona
    from app.models.project_spec import ProjectSpec

    # Verify project exists and belongs to user
    project_result = await db.execute(
        select(ProjectSpec)
        .where(
            ProjectSpec.id == project_id,
            ProjectSpec.tenant_id == current_user.id,
        )
    )
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get personas for this project
    result = await db.execute(
        select(Persona)
        .where(
            Persona.project_id == project_id,
            Persona.is_active == True,
        )
        .offset(skip)
        .limit(limit)
    )
    personas = result.scalars().all()

    return [
        ProjectPersonaResponse(
            id=str(p.id),
            label=p.label,
            source=p.source,
            demographics=p.demographics or {},
            preferences=p.preferences or {},
            perception_weights=p.perception_weights or {},
            bias_parameters=p.bias_parameters or {},
            action_priors=p.action_priors or {},
            uncertainty_score=p.uncertainty_score,
            is_active=p.is_active,
            created_at=p.created_at.isoformat() if p.created_at else "",
        )
        for p in personas
    ]


@router.delete("/project/{project_id}/personas")
async def delete_project_personas(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete all personas for a project.

    This is useful for regenerating personas or cleaning up before a new run.
    """
    from sqlalchemy import delete
    from app.models.persona import Persona
    from app.models.project_spec import ProjectSpec

    # Verify project exists and belongs to user
    project_result = await db.execute(
        select(ProjectSpec)
        .where(
            ProjectSpec.id == project_id,
            ProjectSpec.tenant_id == current_user.id,
        )
    )
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Delete all personas for this project
    await db.execute(
        delete(Persona).where(Persona.project_id == project_id)
    )
    await db.commit()

    return {"message": "Personas deleted successfully", "project_id": str(project_id)}
