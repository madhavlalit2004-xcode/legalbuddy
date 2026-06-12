from app.core.config import settings
from fastapi import FastAPI
from app.core.exceptions import LegalBuddyException, legal_buddy_exception_handler

app = FastAPI(
    title=settings.APP_NAME, 
    version=settings.APP_VERSION,
    debug=settings.DEBUG
)
app.add_exception_handler(LegalBuddyException, legal_buddy_exception_handler)