#!/usr/bin/env python
"""
GraphRAG Server Debug Script
Check configuration and data loading, help troubleshoot issues
"""

import os
import asyncio
import logging
from pathlib import Path
from webserver.configs import settings
from webserver.search import load_context, load_local_search_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    # Display current configuration
    print("\n==== Current Configuration Info ====")
    print(f"Root directory: {settings.root}")
    print(f"Data directory: {settings.data}")
    
    # Check if directories exist
    print("\n==== Checking If Directories Exist ====")
    if os.path.exists(settings.root):
        print(f"✅ Root directory exists: {settings.root}")
        
        # Check settings.yaml
        config_path = os.path.join(settings.root, "settings.yaml")
        if os.path.exists(config_path):
            print(f"✅ Configuration file exists: {config_path}")
            
            # Check file contents
            try:
                import yaml
                with open(config_path, 'r') as f:
                    config_yaml = yaml.safe_load(f)
                
                if config_yaml and isinstance(config_yaml, dict):
                    print(f"✅ Configuration file format is correct")
                    
                    # Check models configuration
                    if 'models' in config_yaml and 'default_chat_model' in config_yaml['models']:
                        model_config = config_yaml['models']['default_chat_model']
                        print(f"✅ Model configuration exists")
                        print(f"   - Model type: {model_config.get('type', 'N/A')}")
                        model_name = model_config.get('model', 'N/A') or model_config.get('model_name', 'N/A')
                        print(f"   - Model name: {model_name}")
                    else:
                        print(f"❌ Model configuration not found, GraphRAG requires models.default_chat_model configuration")
                else:
                    print(f"❌ settings.yaml parsing error or incorrect format")
            except Exception as e:
                print(f"❌ Error reading settings.yaml: {str(e)}")
        else:
            print(f"❌ Configuration file does not exist: {config_path}")
            print(f"   A settings.yaml file must be provided in the external directory!")
    else:
        print(f"❌ Root directory does not exist: {settings.root}")
    
    if os.path.exists(settings.data):
        print(f"✅ Data directory exists: {settings.data}")
        
        # Check necessary data files - only check the latest version
        print("\n==== Checking Data Files ====")
        required_files = [
            "entities.parquet",
            "text_units.parquet",
            "relationships.parquet",
            "community_reports.parquet",
            "communities.parquet",
        ]
        
        found_files = []
        missing_files = []
        for file in required_files:
            file_path = os.path.join(settings.data, file)
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path) / (1024 * 1024)  # Convert to MB
                print(f"✅ File found: {file} ({file_size:.2f} MB)")
                found_files.append(file)
            else:
                print(f"❌ Required file not found: {file}")
                missing_files.append(file)
        
        # Check if all required files are found
        if len(found_files) == len(required_files):
            print(f"✅ Complete GraphRAG 2.1.0 format data files found")
        else:
            print(f"❌ Missing necessary data files: {', '.join(missing_files)}")
            print(f"   GraphRAG server requires all necessary data files in version 2.1.0")
            return
    else:
        print(f"❌ Data directory does not exist: {settings.data}")
        return
    
    # Try to load context and search engine
    print("\n==== Attempting to Load Data ====")
    try:
        root = Path(settings.root)
        data_dir = Path(settings.data)
        
        print(f"Loading configuration from external directory...")
        config_path = root / "settings.yaml"
        if not config_path.exists():
            print(f"❌ No settings.yaml file in external directory: {config_path}")
            return
            
        try:
            print(f"Loading context from external directory...")
            config, data = await load_context(root, data_dir)
            
            # Check if data loaded successfully
            print("\n==== Data Loading Status ====")
            for key, df in data.items():
                if df is not None and not df.empty:
                    print(f"✅ {key}: Successfully loaded {len(df)} records")
                else:
                    print(f"❌ {key}: Failed to load data")
            
            # Try to initialize local search engine
            print("\n==== Initializing Search Engine ====")
            print("Initializing local search engine...")
            search_engine = await load_local_search_engine(config, data)
            
            if search_engine and search_engine._search_engine:
                print("✅ Search engine initialized successfully")
                
                # Check if context data is loaded
                if hasattr(search_engine._search_engine, 'context_data'):
                    for key, value in search_engine._search_engine.context_data.items():
                        if value is not None:
                            print(f"✅ Context data loaded: {key}")
                        else:
                            print(f"❌ Context data not loaded: {key}")
                else:
                    print("❌ Search engine did not initialize context data")
            else:
                print("❌ Search engine initialization failed")
            
        except FileNotFoundError as e:
            print(f"❌ Configuration file error: {str(e)}")
        except Exception as e:
            print(f"❌ Error during loading process: {str(e)}")
            import traceback
            traceback.print_exc()
    except Exception as e:
        print(f"❌ Error during loading process: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 