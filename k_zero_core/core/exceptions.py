class APIVoiceException(Exception):
    """Base exception for the application."""
    pass

class OllamaConnectionError(APIVoiceException):
    """Raised when the Ollama server is unreachable."""
    pass

class NoModelsFoundError(APIVoiceException):
    """Raised when Ollama is running but no models are downloaded."""
    pass

class StorageError(APIVoiceException):
    """Raised when there is an issue reading or writing local data."""
    pass
