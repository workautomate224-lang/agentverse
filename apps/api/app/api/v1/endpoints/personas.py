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
