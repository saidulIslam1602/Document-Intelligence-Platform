"""Mock services for local development"""

from .azure_mocks import MockFormRecognizer, MockCognitiveSearch, MockOpenAI

__all__ = ['MockFormRecognizer', 'MockCognitiveSearch', 'MockOpenAI']
