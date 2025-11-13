# src/template_routes.py
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from .template_schemas import (
    TemplateCreate, TemplateUpdate, TemplateResponse,
    RenderedTemplate, TemplateRenderRequest, TemplateVersionResponse,
    TemplateStatus, TemplateType
)
from .template_service import template_service
from src.db.main import get_template_db

router = APIRouter(prefix="/api/v1/templates", tags=["templates"])

@router.post("/", response_model=TemplateResponse)
async def create_template(template_data: TemplateCreate, db: AsyncSession = Depends(get_template_db)):
   
    try:
        template = await template_service.create_template(template_data, db)
        return template
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{template_code}", response_model=TemplateResponse)
async def get_template(template_code: str, language: str = "en", version: Optional[int] = None, db: AsyncSession = Depends(get_template_db)):
    """
    Get template by code
    """
    try:
        template = await template_service.get_template(template_code, language, version, db)
        return template
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{template_code}/render", response_model=RenderedTemplate)
async def render_template(template_code: str, render_request: TemplateRenderRequest, db: AsyncSession = Depends(get_template_db)):
    """
    Render template with variables
    """
    try:
        rendered = await template_service.render_template(
            template_code=template_code,
            variables=render_request.variables,
            language=render_request.language,
            db=db
        )
        return rendered
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{template_code}", response_model=TemplateResponse)
async def update_template(template_code: str, language: str, update_data: TemplateUpdate, db: AsyncSession = Depends(get_template_db)):
    """
    Update template (creates new version)
    """
    try:
        template = await template_service.update_template(template_code, language, update_data, db)
        return template
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[TemplateResponse])
async def list_templates(
    status: Optional[TemplateStatus] = None,
    template_type: Optional[TemplateType] = None,
    db: AsyncSession = Depends(get_template_db)
):
    """
    List all templates
    """
    templates = await template_service.list_templates(status, template_type, db)
    return templates

@router.get("/{template_code}/versions", response_model=List[TemplateVersionResponse])
async def get_template_versions(template_code: str, language: str = "en", db: AsyncSession = Depends(get_template_db)):
    """
    Get template version history
    """
    versions = await template_service.get_template_versions(template_code, language, db)
    return versions

@router.delete("/{template_code}")
async def archive_template(template_code: str, language: str = "en", db: AsyncSession = Depends(get_template_db)):
    """
    Archive a template
    """
    try:
        update_data = TemplateUpdate(status=TemplateStatus.ARCHIVED, change_reason="Archived by user")
        await template_service.update_template(template_code, language, update_data, db)
        return {"message": f"Template {template_code} archived successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))