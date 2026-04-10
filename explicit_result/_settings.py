import os

class Settings:
    """
    Global configuration for the Resolute library.
    
    Settings can be controlled via environment variables:
    - RESOLUTE_VERBOSE_ERROR: Set to '0' or 'false' to disable full tracebacks in Err summaries.
    """
    
    @property
    def verbose_error(self) -> bool:
        """
        Whether Err.__str__ should include the full exception traceback.
        Defaults to True unless RESOLUTE_VERBOSE_ERROR is '0' or 'false'.
        """
        val = os.getenv("RESOLUTE_VERBOSE_ERROR", "1").lower()
        return val not in ("0", "false", "no", "off")

settings = Settings()
