from fastapi import Request
from fastapi.responses import JSONResponse

class LegalBuddyException(Exception):
    def __init__(self, message, status_code = 500 , error_code = "INTERNAL_ERROR"):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code

        super().__init__(message)
    
    async def legal_buddy_exception_handler(request, exc):
        return JSONResponse(
            status_code=exc.status_code, 
            content={
                "error": exc.error_code,
                "message": exc.message,
                "status_code": exc.status_code
            }
        )

#Documents Exceptions
class FileTooLargeException(LegalBuddyException):
    def __init__(self, message = "This File you uploded is too Large"):
        super().__init__(message, status_code = 400, error_code = "FILE_TOO_LARGE")

class FileNotPDForDOCXException(LegalBuddyException):
    def __init__(self, message = "File is not of the valid Format"):
        super().__init__(message, status_code = 400, error_code = "INVALID_FILE_FORMAT")

class FileCorruptedException(LegalBuddyException):
    def __init__(self, message = "File is Corrupted"):
        super().__init__(message, status_code = 400, error_code = "CORRUPTED_FILE")

class FileUnreadableException(LegalBuddyException):
    def __init__(self, message = "File is unreadable"):
        super().__init__(message, status_code = 400, error_code = "UNREADABLE_FILE")

class FileParsingException(LegalBuddyException):
    def __init__(self, message = "File Parsing Failed"):
        super().__init__(message, status_code = 400, error_code = "PARSING_FAILED")


#LLM
class OllamaUnreachableException(LegalBuddyException):
    def __init__(self, message = "Ollama service is unreachable"):
        super().__init__(message, status_code = 503, error_code = "LLM_UNREACHABLE")

class ModelNotFoundException(LegalBuddyException):
    def __init__(self, message = "Model not found for LLM"):
        super().__init__(message, status_code = 503, error_code = "MODEL_NOT_FOUND")

class GenerationFailedException(LegalBuddyException):
    def __init__(self, message = "Generation not done"):
        super().__init__(message, status_code = 503, error_code = "GENERATIONAL_ERROR")


#VectorDB
class StorageException(LegalBuddyException):
    def __init__(self, message = "Storage is Full"):
        super().__init__(message, status_code = 503, error_code = "STORAGE_FULL")

class CollectionException(LegalBuddyException):
    def __init__(self, message = "Collection not found"):
        super().__init__(message, status_code = 503, error_code = "COLLECTION_NOT_FOUND")

class EmbeddingException(LegalBuddyException):
    def __init__(self, message = "Embedding of data Failed"):
        super().__init__(message, status_code = 503, error_code = "EMBEDDING_FAILED")
    

#Authorization
class TokenExpireException(LegalBuddyException):
    def __init__(self, message = "Tokens are expired"):
        super().__init__(message, status_code = 401, error_code = "TOKEN_EXPIRED")
    
class TokenInvalidException(LegalBuddyException):
    def __init__(self, message = "Invalid Tokens Found"):
        super().__init__(message, status_code = 401, error_code = "INVALID_TOKENS")
    
class UserNotFoundException(LegalBuddyException):
    def __init__(self, message = "User not found"):
        super().__init__(message, status_code = 404, error_code = "USER_NOT_FOUND")


#Validation
class EmptyQuestionException(LegalBuddyException):
    def __init__(self, message = "No question Found"):
        super().__init__(message, status_code = 422, error_code = "EMPTY_QUESTION")

class InvalidQuestionException(LegalBuddyException):
    def __init__(self, message = "Not a valid Question"):
        super().__init__(message, status_code = 422, error_code = "INVALID_QUESTION")

class MissingReqFieldException(LegalBuddyException):
    def __init__(self, message = "Required fields are missing"):
        super().__init__(message, status_code = 422, error_code = "MISSING_FIELD")

class ValueOutOfRangeException(LegalBuddyException):
    def __init__(self, message = "Values are out of Range"):
        super().__init__(message, status_code = 422, error_code = "VALUE_OUT_OF_BOUNDS")