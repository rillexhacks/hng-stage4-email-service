# src/template_service.py
import logging
from typing import List, Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from src.db.main import get_template_db
from .template_models import EmailTemplate, TemplateVersion, TemplateStatus, TemplateType
from .template_schemas import TemplateCreate, TemplateUpdate, RenderedTemplate
from .template_renderer import template_renderer

logger = logging.getLogger(__name__)

class TemplateService:
    
    async def create_template(self, template_data: TemplateCreate, db: AsyncSession) -> EmailTemplate:
        """
        Create a new email template
        """
        # Check if template code already exists
        result = await db.execute(
            select(EmailTemplate).where(
                and_(
                    EmailTemplate.template_code == template_data.template_code,
                    EmailTemplate.language == template_data.language,
                    EmailTemplate.is_current == True
                )
            )
        )
        existing_template = result.scalar_one_or_none()
        
        if existing_template:
            raise ValueError(f"Template with code '{template_data.template_code}' and language '{template_data.language}' already exists")
        
        # Extract variables from templates
        all_text = f"{template_data.subject} {template_data.body_html} {template_data.body_text or ''}"
        detected_variables = template_renderer.extract_variables(all_text)
        
        # Create new template
        template = EmailTemplate(
            template_code=template_data.template_code,
            name=template_data.name,
            description=template_data.description,
            subject=template_data.subject,
            body_html=template_data.body_html,
            body_text=template_data.body_text,
            template_type=template_data.template_type,
            language=template_data.language,
            variables=detected_variables,
            created_by=template_data.created_by
        )
            
        db.add(template)
        await db.commit()
        await db.refresh(template)
        
        logger.info(f"Created template: {template_data.template_code} v{template.version}")
        return template
    
    async def get_template(self, template_code: str, language: str = "en", version: Optional[int] = None, db: AsyncSession = None) -> EmailTemplate:
        """
        Get template by code and language
        """
        query = select(EmailTemplate).where(
            and_(
                EmailTemplate.template_code == template_code,
                EmailTemplate.language == language
            )
        )
        
        if version:
            query = query.where(EmailTemplate.version == version)
        else:
            query = query.where(EmailTemplate.is_current == True)
        
        result = await db.execute(query)
        template = result.scalar_one_or_none()
        
        if not template:
            raise ValueError(f"Template not found: {template_code} (language: {language})")
        
        return template
    
    async def render_template(self, template_code: str, variables: Dict[str, str], language: str = "en", db: AsyncSession = None) -> RenderedTemplate:
        """
        Render template with variables
        """
        template = await self.get_template(template_code, language, None, db)
        
        # Check if all required variables are provided
        missing_vars = set(template.variables or []) - set(variables.keys())
        if missing_vars:
            raise ValueError(f"Missing template variables: {missing_vars}")
        
        # Render template
        rendered = template_renderer.render_template(
            subject=template.subject,
            body_html=template.body_html,
            body_text=template.body_text,
            variables=variables
        )
        
        return RenderedTemplate(
            template_code=template_code,
            language=language,
            subject=rendered["subject"],
            body_html=rendered["body_html"],
            body_text=rendered["body_text"]
        )
    
    async def update_template(self, template_code: str, language: str, update_data: TemplateUpdate, db: AsyncSession) -> EmailTemplate:
        """
        Update template (creates new version)
        """
        # Get current template
        result = await db.execute(
            select(EmailTemplate).where(
                and_(
                    EmailTemplate.template_code == template_code,
                    EmailTemplate.language == language,
                    EmailTemplate.is_current == True
                )
            )
        )
        current_template = result.scalar_one_or_none()
        
        if not current_template:
            # Debug: Check if template exists with different criteria
            debug_result = await db.execute(
                select(EmailTemplate).where(
                    EmailTemplate.template_code == template_code
                )
            )
            debug_templates = debug_result.scalars().all()
            logger.error(f"Template '{template_code}' not found with is_current=True and language='{language}'. Found {len(debug_templates)} templates with this code.")
            for tmpl in debug_templates:
                logger.error(f"  - Template: code={tmpl.template_code}, language={tmpl.language}, is_current={tmpl.is_current}, version={tmpl.version}")
            raise ValueError(f"Template not found: {template_code} (language: {language})")
        
        # Archive current version
        current_template.is_current = False
        await db.commit()
        
        # Create new version
        new_version = current_template.version + 1
        
        # Extract variables from updated templates
        all_text = f"{update_data.subject or current_template.subject} {update_data.body_html or current_template.body_html} {update_data.body_text or current_template.body_text or ''}"
        detected_variables = template_renderer.extract_variables(all_text)
        
        # Create new template version
        new_template = EmailTemplate(
            template_code=current_template.template_code,
            name=update_data.name or current_template.name,
            description=update_data.description or current_template.description,
            subject=update_data.subject or current_template.subject,
            body_html=update_data.body_html or current_template.body_html,
            body_text=update_data.body_text or current_template.body_text,
            template_type=current_template.template_type,
            language=current_template.language,
            variables=detected_variables,
            status=update_data.status or current_template.status,
            version=new_version,
            is_current=True,
            created_by=current_template.created_by
        )
        
        # Create version history record
        version_history = TemplateVersion(
            template_code=current_template.template_code,
            version=current_template.version,
            subject=current_template.subject,
            body_html=current_template.body_html,
            body_text=current_template.body_text,
            variables=current_template.variables,
            change_reason=update_data.change_reason,
            created_by=current_template.created_by
        )
        
        db.add(new_template)
        db.add(version_history)
        await db.commit()
        await db.refresh(new_template)
        
        logger.info(f"Updated template: {template_code} v{new_version}")
        return new_template
    
    async def list_templates(self, status: Optional[TemplateStatus] = None, template_type: Optional[TemplateType] = None, db: AsyncSession = None) -> List[EmailTemplate]:
        """
        List all current templates
        """
        query = select(EmailTemplate).where(EmailTemplate.is_current == True)
        
        if status:
            query = query.where(EmailTemplate.status == status)
        
        if template_type:
            query = query.where(EmailTemplate.template_type == template_type)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_template_versions(self, template_code: str, language: str = "en", db: AsyncSession = None) -> List[TemplateVersion]:
        """
        Get version history for a template
        """
        result = await db.execute(
            select(TemplateVersion).where(
                TemplateVersion.template_code == template_code
            ).order_by(TemplateVersion.version.desc())
        )
        return result.scalars().all()

# Global instance
template_service = TemplateService()
