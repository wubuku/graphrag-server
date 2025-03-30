#!/usr/bin/env python
"""
GraphRAG Environment Check Tool
Check if environment variables and configuration settings are correct
"""

import os
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("env-checker")

# Check python-dotenv
dotenv_installed = False
try:
    import dotenv
    dotenv.load_dotenv()
    dotenv_installed = True
except ImportError:
    pass

def main():
    # Check environment variables
    logger.info("==== Checking Environment Variables ====")
    
    # Ensure python-dotenv is correctly imported
    if dotenv_installed:
        logger.info("✅ python-dotenv is correctly installed and imported")
    else:
        logger.error("❌ python-dotenv is not installed, please run: pip install python-dotenv")
        
    # Check necessary environment variables
    essential_vars = {
        "GRAPHRAG_API_KEY": os.environ.get("GRAPHRAG_API_KEY", ""),
        "GRAPHRAG_ROOT_DIR": os.environ.get("GRAPHRAG_ROOT_DIR", ""),
        "GRAPHRAG_DATA_DIR": os.environ.get("GRAPHRAG_DATA_DIR", ""),
    }
    
    for var_name, var_value in essential_vars.items():
        if var_value:
            # For API keys, only display the first few characters
            if "API_KEY" in var_name and len(var_value) > 8:
                display_value = var_value[:8] + "..." + var_value[-4:]
            else:
                display_value = var_value
            logger.info(f"✅ {var_name} = {display_value}")
        else:
            if var_name == "GRAPHRAG_API_KEY":
                logger.warning(f"⚠️ {var_name} is not set, this may cause problems if using APIs that require authentication")
            else:
                logger.error(f"❌ {var_name} is not set")
    
    # Check if directories exist
    logger.info("\n==== Checking If Directories Exist ====")
    root_dir = os.environ.get("GRAPHRAG_ROOT_DIR", "")
    data_dir = os.environ.get("GRAPHRAG_DATA_DIR", "")
    
    if root_dir and os.path.exists(root_dir):
        logger.info(f"✅ Root directory exists: {root_dir}")
        
        # Check settings.yaml
        settings_file = os.path.join(root_dir, "settings.yaml")
        if os.path.exists(settings_file):
            logger.info(f"✅ Settings file exists: {settings_file}")
            
            # Check file contents
            try:
                import yaml
                with open(settings_file, 'r') as f:
                    settings = yaml.safe_load(f)
                
                if settings and isinstance(settings, dict):
                    # Check model configuration
                    if 'models' in settings and 'default_chat_model' in settings['models']:
                        logger.info(f"✅ Model configuration exists")
                        model_config = settings['models']['default_chat_model']
                        model_type = model_config.get('type', '')
                        model_name = model_config.get('model_name', '') or model_config.get('model', '')
                        logger.info(f"   - Model type: {model_type}")
                        logger.info(f"   - Model name: {model_name}")
                    else:
                        logger.error(f"❌ Model configuration not found")
                else:
                    logger.error(f"❌ settings.yaml parsing error")
            except Exception as e:
                logger.error(f"❌ Error reading settings.yaml: {str(e)}")
        else:
            logger.error(f"❌ Settings file does not exist: {settings_file}")
    else:
        logger.error(f"❌ Root directory does not exist: {root_dir}")
    
    if data_dir and os.path.exists(data_dir):
        logger.info(f"✅ Data directory exists: {data_dir}")
        
        # Check necessary data files - only check new version files
        logger.info("\n==== Checking Data Files ====")
        required_files = [
            "entities.parquet",
            "text_units.parquet",
            "relationships.parquet",
            "community_reports.parquet",
            "communities.parquet"
        ]
        
        missing_files = []
        for file in required_files:
            file_path = os.path.join(data_dir, file)
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path) / (1024 * 1024)  # Convert to MB
                logger.info(f"✅ File found: {file} ({file_size:.2f} MB)")
            else:
                missing_files.append(file)
                logger.error(f"❌ Required file not found: {file}")
        
        if not missing_files:
            logger.info(f"✅ All required GraphRAG 2.1.0 format data files found")
        else:
            logger.error(f"❌ Missing necessary data files: {', '.join(missing_files)}")
    else:
        logger.error(f"❌ Data directory does not exist: {data_dir}")
    
    # Check Python packages and dependencies
    logger.info("\n==== Checking Python Package Dependencies ====")
    required_packages = [
        "fastapi", "uvicorn", "graphrag", 
        "pandas", "pydantic", "pyarrow"
    ]
    
    # Handle python-dotenv separately as we've already checked it at the top
    if dotenv_installed:
        logger.info(f"✅ python-dotenv is installed (version: {getattr(dotenv, '__version__', 'unknown')})")
    
    for package in required_packages:
        try:
            # Try importing directly instead of using importlib.util.find_spec
            module = __import__(package)
            version = getattr(module, "__version__", "unknown")
            logger.info(f"✅ {package} is installed (version: {version})")
            
            # Check graphrag version
            if package == "graphrag" and hasattr(module, "__version__"):
                graphrag_version = module.__version__
                if graphrag_version >= "2.1.0":
                    logger.info(f"   - GraphRAG version {graphrag_version} meets requirements")
                else:
                    logger.warning(f"⚠️ GraphRAG version {graphrag_version} is outdated, recommend upgrading to 2.1.0+")
        except ImportError:
            logger.error(f"❌ {package} is not installed")
    
    logger.info("\n==== Environment Check Complete ====")

if __name__ == "__main__":
    main() 