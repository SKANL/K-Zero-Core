class APIVoiceException(Exception):
    """Base exception for the application."""

class OllamaConnectionError(APIVoiceException):
    """Raised when the Ollama server is unreachable."""

class NoModelsFoundError(APIVoiceException):
    """Raised when Ollama is running but no models are downloaded."""

class StorageError(APIVoiceException):
    """Raised when there is an issue reading or writing local data."""

class WebToolError(APIVoiceException):
    """Raised when a web scraping or search tool fails due to network or parsing issues."""
