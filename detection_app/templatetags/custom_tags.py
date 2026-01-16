from django import template
from detection_app.models import AssessmentResult, SpiralAssessmentResult, AssessmentHistory, BrainScanResult

register = template.Library()

@register.filter(name='instanceof')
def isinstanceof(obj, class_name):
    return obj.__class__.__name__ == class_name
