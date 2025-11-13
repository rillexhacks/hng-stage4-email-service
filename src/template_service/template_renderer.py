# src/template_renderer.py
import logging
from typing import Dict, Optional
from jinja2 import Template, Environment, BaseLoader, StrictUndefined
import re

logger = logging.getLogger(__name__)

class TemplateRenderer:
    def __init__(self):
        # Create Jinja2 environment with strict undefined to catch missing variables
        self.env = Environment(
            loader=BaseLoader(),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True
        )
    
    def render_template(self, subject: str, body_html: str, body_text: Optional[str], variables: Dict[str, str]) -> Dict[str, str]:
        """
        Render email template with variables
        
        Args:
            subject: Template subject with variables
            body_html: HTML template with variables
            body_text: Plain text template with variables
            variables: Dictionary of variable values
        
        Returns:
            Dict with rendered subject, body_html, and body_text
        
        Raises:
            ValueError: If required variables are missing
        """
        try:
            # Render subject
            subject_template = self.env.from_string(subject)
            rendered_subject = subject_template.render(**variables)
            
            # Render HTML body
            html_template = self.env.from_string(body_html)
            rendered_html = html_template.render(**variables)
            
            # Render text body (if provided)
            rendered_text = None
            if body_text:
                text_template = self.env.from_string(body_text)
                rendered_text = text_template.render(**variables)
            
            return {
                "subject": rendered_subject,
                "body_html": rendered_html,
                "body_text": rendered_text
            }
            
        except Exception as e:
            logger.error(f"Template rendering failed: {str(e)}")
            raise ValueError(f"Template rendering error: {str(e)}")
    
    def extract_variables(self, text: str) -> list:
        """
        Extract all template variables from text
        """
        if not text:
            return []
        
        # Find all {{variable}} patterns
        pattern = r'{{\s*(\w+)\s*}}'
        variables = re.findall(pattern, text)
        return list(set(variables))  # Remove duplicates

# Global instance
template_renderer = TemplateRenderer()