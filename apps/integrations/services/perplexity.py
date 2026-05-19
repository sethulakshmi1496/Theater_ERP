import requests
import json
import logging
from datetime import datetime
from apps.integrations.models import IntegrationConnector
from apps.reports.models import AIInsightReport, AIActionItem

logger = logging.getLogger(__name__)

class PerplexityService:
    BASE_URL = "https://api.perplexity.ai/chat/completions"
    
    @classmethod
    def get_api_key(cls, tenant):
        try:
            connector = IntegrationConnector.objects.get(
                tenant=tenant,
                connector_name=IntegrationConnector.ConnectorName.PERPLEXITY,
                is_active=True
            )
            return connector.credentials_json.get('api_key')
        except IntegrationConnector.DoesNotExist:
            return None

    @classmethod
    def generate_report(cls, tenant, report_type, period_type, module, start_date, end_date, context_data, prompt_template):
        api_key = cls.get_api_key(tenant)
        if not api_key:
            logger.error(f"Perplexity API key not found or inactive for tenant {tenant.id}")
            return None
            
        system_prompt = (
            "You are an AI intelligence layer for AEC Cinemas. "
            "Analyze the provided context and return a structured JSON response. "
            "The JSON must have the following keys: "
            "'summary' (string), "
            "'suggestions' (list of strings), "
            "'risks' (list of strings), "
            "'opportunities' (list of strings), "
            "'benchmark_notes' (string), "
            "'severity' (string: INFO, LOW, MEDIUM, HIGH, CRITICAL)."
        )
        
        user_prompt = f"Template: {prompt_template}\n\nContext:\n{json.dumps(context_data, indent=2, default=str)}"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "sonar-pro",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
        }
        
        try:
            start_time = datetime.now()
            response = requests.post(cls.BASE_URL, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            response_data = response.json()
            end_time = datetime.now()
            
            content = response_data['choices'][0]['message']['content']
            
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].strip()
                
            parsed_content = json.loads(content)
            
            report = AIInsightReport.objects.create(
                tenant=tenant,
                report_type=report_type,
                period_type=period_type,
                module=module,
                start_date=start_date,
                end_date=end_date,
                summary=parsed_content.get('summary', 'No summary provided.'),
                suggestions=parsed_content.get('suggestions', []),
                risks=parsed_content.get('risks', []),
                opportunities=parsed_content.get('opportunities', []),
                benchmark_notes=parsed_content.get('benchmark_notes', ''),
                severity=parsed_content.get('severity', 'INFO').upper(),
                source_metadata={
                    "model": response_data.get('model'),
                    "duration_ms": (end_time - start_time).total_seconds() * 1000,
                    "usage": response_data.get('usage', {})
                }
            )
            
            for suggestion in parsed_content.get('suggestions', []):
                AIActionItem.objects.create(
                    report=report,
                    description=suggestion
                )
                
            return report
            
        except Exception as e:
            logger.error(f"Error generating Perplexity report: {str(e)}")
            return None
