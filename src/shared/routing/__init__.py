"""
Intelligent Document Routing Module

Automatically routes documents to optimal processing mode:
- Traditional API: Fast, cost-effective (85% of documents)
- Multi-Agent: Intelligent orchestration (15% complex documents)
- MCP: External AI agent integration (user-initiated)
"""

from .intelligent_router import (
    IntelligentDocumentRouter,
    DocumentComplexityAnalyzer,
    ProcessingMode,
    ComplexityLevel,
    get_document_router
)

__all__ = [
    'IntelligentDocumentRouter',
    'DocumentComplexityAnalyzer',
    'ProcessingMode',
    'ComplexityLevel',
    'get_document_router'
]

