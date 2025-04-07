import os
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    server_port: int = 20213
    cors_allowed_origins: list = ["*"]  # Edit the list to restrict access.
    
    # Configuration overridden by environment variables, ensure paths are absolute
    root: str = os.environ.get("GRAPHRAG_ROOT_DIR", ".")
    data: str = os.environ.get("GRAPHRAG_DATA_DIR", "")
    
    # Base URL for references, used in response links
    # Can be set to external domain when using reverse proxy
    reference_base_url: str = os.environ.get("GRAPHRAG_REFERENCE_BASE_URL", "")
    
    community_level: int = 2
    dynamic_community_selection: bool = False
    response_type: str = "Multiple Paragraphs"
    # Controls whether to show references in responses
    show_references: bool = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure paths are absolute
        self.root = os.path.abspath(os.path.expanduser(self.root))
        
        # If data is not set, use root/output as default
        if not self.data:
            self.data = os.path.join(self.root, "output")
        else:
            self.data = os.path.abspath(os.path.expanduser(self.data))
        
        # Explicitly handle boolean environment variables
        show_refs_env = os.environ.get("GRAPHRAG_SHOW_REFERENCES", "").lower()
        if show_refs_env in ("false", "0", "no", "n", "off"):
            self.show_references = False
        elif show_refs_env in ("true", "1", "yes", "y", "on"):
            self.show_references = True
            
        # Print current path configuration for debugging
        print(f"GraphRAG Root Dir: {self.root}")
        print(f"GraphRAG Data Dir: {self.data}")
        print(f"Show References: {self.show_references}")

    @property
    def website_address(self) -> str:
        return f"http://127.0.0.1:{self.server_port}"
        
    @property
    def reference_url_base(self) -> str:
        """Get the base URL for references
        
        If reference_base_url is set, use it; otherwise use website_address
        """
        if self.reference_base_url:
            return self.reference_base_url.rstrip('/')
        return self.website_address

    class Config:
        env_prefix = "GRAPHRAG_"
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Allow additional environment variables


settings = Settings()
