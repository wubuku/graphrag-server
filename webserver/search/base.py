import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, Union, Tuple, List

import pandas as pd
import graphrag.api as api
from graphrag.config.load_config import load_config
from graphrag.config.models.graph_rag_config import GraphRagConfig
from graphrag.callbacks.noop_query_callbacks import NoopQueryCallbacks
from graphrag.utils.api import create_storage_from_config
from graphrag.utils.storage import load_table_from_storage, storage_has_table

from webserver.utils import consts

logger = logging.getLogger(__name__)

async def load_context(root: Union[Path, str], data_dir: Optional[Union[Path, str]] = None) -> Tuple[GraphRagConfig, Dict[str, pd.DataFrame]]:
    """
    Load GraphRAG configuration and data files
    
    Parameters:
        root: Root directory containing the configuration file or configuration dictionary
        data_dir: Data directory, if None, the path specified in the configuration will be used
    
    Returns:
        config: GraphRAG configuration object
        dataframe_dict: Dictionary of loaded data files
    """
    # Ensure paths are Path objects
    if isinstance(root, str):
        root = Path(root)
    if isinstance(data_dir, str) and data_dir is not None:
        data_dir = Path(data_dir)
    
    # Load configuration
    cli_overrides = {}
    if data_dir:
        cli_overrides["output.base_dir"] = str(data_dir)
    
    config = load_config(root, None, cli_overrides)
    
    # Load data files
    dataframe_dict = await resolve_output_files(
        config=config,
        output_list=[
            consts.TEXT_UNIT_TABLE,           
            consts.ENTITY_TABLE,            
            consts.COMMUNITY_TABLE,         
            consts.COMMUNITY_REPORT_TABLE,   
            consts.RELATIONSHIP_TABLE,       
        ],
        optional_list=[
            consts.DOCUMENT_TABLE,
        ],
    )
    
    return config, dataframe_dict

async def resolve_output_files(
    config: GraphRagConfig,
    output_list: List[str],
    optional_list: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Parse and load output files"""
    logger.info(f"Parsing output files")
    
    dataframe_dict = {}
    
    # Check if using multi-index configuration
    if hasattr(config, 'outputs') and config.outputs:
        # Multi-index search
        dataframe_dict["multi-index"] = True
        dataframe_dict["num_indexes"] = len(config.outputs)
        dataframe_dict["index_names"] = config.outputs.keys()
        
        for output in config.outputs.values():
            storage_obj = create_storage_from_config(output)
            for name in output_list:
                if name not in dataframe_dict:
                    dataframe_dict[name] = []
                
                if await storage_has_table(name, storage_obj):
                    df_value = await load_table_from_storage(name=name, storage=storage_obj)
                    dataframe_dict[name].append(df_value)
        
        # Process optional files
        if optional_list:
            for optional_file in optional_list:
                if optional_file not in dataframe_dict:
                    dataframe_dict[optional_file] = []
                
                for output in config.outputs.values():
                    storage_obj = create_storage_from_config(output)
                    if await storage_has_table(optional_file, storage_obj):
                        df_value = await load_table_from_storage(name=optional_file, storage=storage_obj)
                        dataframe_dict[optional_file].append(df_value)
    else:
        # Single-index search
        dataframe_dict["multi-index"] = False
        storage_obj = create_storage_from_config(config.output)
        
        for name in output_list:
            if await storage_has_table(name, storage_obj):
                df_value = await load_table_from_storage(name=name, storage=storage_obj)
                dataframe_dict[name] = df_value
            else:
                logger.warning(f"Required file not found: {name}")
                dataframe_dict[name] = None
        
        # Process optional files
        if optional_list:
            for optional_file in optional_list:
                if await storage_has_table(optional_file, storage_obj):
                    df_value = await load_table_from_storage(name=optional_file, storage=storage_obj)
                    dataframe_dict[optional_file] = df_value
                else:
                    dataframe_dict[optional_file] = None
    
    return dataframe_dict

class SearchEngineHandler:
    def __init__(self, config, data):
        self.config = config
        self.data = data
        self.engine_type = consts.INDEX_BASIC  # Default to basic search
    
    async def search(self, query, **kwargs):
        """Execute search using GraphRAG API"""
        logger.info(f"Executing GraphRAG search: {query}, engine type: {self.engine_type}")
        
        try:
            # Select API based on engine type
            if (self.engine_type == consts.INDEX_GLOBAL and 
                consts.ENTITY_TABLE in self.data and 
                consts.COMMUNITY_TABLE in self.data and 
                consts.COMMUNITY_REPORT_TABLE in self.data):
                # Global search
                response, context_data = await api.global_search(
                    config=self.config,
                    entities=self.data[consts.ENTITY_TABLE],
                    communities=self.data[consts.COMMUNITY_TABLE],
                    community_reports=self.data[consts.COMMUNITY_REPORT_TABLE],
                    query=query
                )
                
                return {
                    "answer": response,
                    "query": query,
                    "context": context_data.get("context", []),
                    "sources": context_data.get("sources", []),
                }
            
            elif (self.engine_type == consts.INDEX_LOCAL and
                  all(k in self.data and self.data[k] is not None for k in 
                      [consts.ENTITY_TABLE, consts.TEXT_UNIT_TABLE, consts.RELATIONSHIP_TABLE, 
                      consts.COMMUNITY_REPORT_TABLE])):
                # Local search
                logger.info(f"Executing local search")
                response, context_data = await api.local_search(
                    config=self.config,
                    entities=self.data[consts.ENTITY_TABLE],
                    text_units=self.data[consts.TEXT_UNIT_TABLE],
                    relationships=self.data[consts.RELATIONSHIP_TABLE],
                    community_reports=self.data[consts.COMMUNITY_REPORT_TABLE],
                    communities=self.data.get(consts.COMMUNITY_TABLE),
                    covariates=None,
                    community_level=consts.COMMUNITY_LEVEL,
                    response_type="full",
                    query=query
                )
                
                return {
                    "answer": response,
                    "query": query,
                    "context": context_data.get("context", []),
                    "sources": context_data.get("sources", []),
                }
                
            elif (self.engine_type == consts.INDEX_DRIFT and 
                  all(k in self.data and self.data[k] is not None for k in 
                      [consts.ENTITY_TABLE, consts.COMMUNITY_TABLE, consts.COMMUNITY_REPORT_TABLE, 
                       consts.TEXT_UNIT_TABLE, consts.RELATIONSHIP_TABLE])):
                # DRIFT search
                response, context_data = await api.drift_search(
                    config=self.config,
                    entities=self.data[consts.ENTITY_TABLE],
                    communities=self.data[consts.COMMUNITY_TABLE],
                    community_reports=self.data[consts.COMMUNITY_REPORT_TABLE],
                    text_units=self.data[consts.TEXT_UNIT_TABLE],
                    relationships=self.data[consts.RELATIONSHIP_TABLE],
                    query=query
                )
                
                return {
                    "answer": response,
                    "query": query,
                    "context": context_data.get("context", []),
                    "sources": context_data.get("sources", []),
                }
                
            elif consts.TEXT_UNIT_TABLE in self.data and self.data[consts.TEXT_UNIT_TABLE] is not None:
                # Basic search
                response, context_data = await api.basic_search(
                    config=self.config,
                    text_units=self.data[consts.TEXT_UNIT_TABLE],
                    query=query
                )
                
                return {
                    "answer": response,
                    "query": query,
                    "context": context_data.get("context", []),
                    "sources": context_data.get("sources", []),
                }
                
            else:
                logger.warning("Missing required data, cannot execute search")
                return {
                    "error": "Missing required data",
                    "answer": "Search engine is not properly configured. Please ensure text data is uploaded and configuration is correct.",
                    "query": query
                }
                
        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            return {
                "error": str(e),
                "answer": f"Error during search: {str(e)}",
                "query": query
            }
    
    async def set_search_engine(self, engine_name):
        """Set the current search engine to use"""
        engine_map = {
            "LocalSearch": consts.INDEX_LOCAL,
            "GlobalSearch": consts.INDEX_GLOBAL, 
            "DRIFTSearch": consts.INDEX_DRIFT,
            "BasicSearch": consts.INDEX_BASIC
        }
        
        if engine_name in engine_map:
            self.engine_type = engine_map[engine_name]
            logger.info(f"Setting search engine: {engine_name}")
            return True
        else:
            logger.warning(f"Unknown search engine type: {engine_name}")
            return False
    
    def get_available_engines(self):
        """Get the list of available search engines"""
        return ["BasicSearch", "LocalSearch", "GlobalSearch", "DRIFTSearch"]
    
    async def stream_search(self, query, **kwargs):
        """Stream search using GraphRAG API"""
        logger.info(f"Executing GraphRAG stream search: {query}, engine type: {self.engine_type}")
        
        callbacks = NoopQueryCallbacks()
        
        try:
            # Select API based on engine type
            if (self.engine_type == consts.INDEX_GLOBAL and 
                consts.ENTITY_TABLE in self.data and 
                consts.COMMUNITY_TABLE in self.data and 
                consts.COMMUNITY_REPORT_TABLE in self.data):
                # Global search
                async for chunk in api.global_search_streaming(
                    config=self.config,
                    entities=self.data[consts.ENTITY_TABLE],
                    communities=self.data[consts.COMMUNITY_TABLE],
                    community_reports=self.data[consts.COMMUNITY_REPORT_TABLE],
                    query=query,
                    callbacks=[callbacks]
                ):
                    yield chunk
            
            elif (self.engine_type == consts.INDEX_LOCAL and
                  all(k in self.data and self.data[k] is not None for k in 
                      [consts.ENTITY_TABLE, consts.TEXT_UNIT_TABLE, consts.RELATIONSHIP_TABLE, 
                      consts.COMMUNITY_REPORT_TABLE])):
                # Local search
                logger.info(f"Executing local stream search")
                async for chunk in api.local_search_streaming(
                    config=self.config,
                    entities=self.data[consts.ENTITY_TABLE],
                    text_units=self.data[consts.TEXT_UNIT_TABLE],
                    relationships=self.data[consts.RELATIONSHIP_TABLE],
                    community_reports=self.data[consts.COMMUNITY_REPORT_TABLE],
                    communities=self.data.get(consts.COMMUNITY_TABLE),
                    covariates=None,
                    community_level=consts.COMMUNITY_LEVEL,
                    response_type="full",
                    query=query,
                    callbacks=[callbacks]
                ):
                    yield chunk
                    
            elif (self.engine_type == consts.INDEX_DRIFT and 
                  all(k in self.data and self.data[k] is not None for k in 
                      [consts.ENTITY_TABLE, consts.COMMUNITY_TABLE, consts.COMMUNITY_REPORT_TABLE, 
                       consts.TEXT_UNIT_TABLE, consts.RELATIONSHIP_TABLE])):
                # DRIFT search
                async for chunk in api.drift_search_streaming(
                    config=self.config,
                    entities=self.data[consts.ENTITY_TABLE],
                    communities=self.data[consts.COMMUNITY_TABLE],
                    community_reports=self.data[consts.COMMUNITY_REPORT_TABLE],
                    text_units=self.data[consts.TEXT_UNIT_TABLE],
                    relationships=self.data[consts.RELATIONSHIP_TABLE],
                    query=query,
                    callbacks=[callbacks]
                ):
                    yield chunk
                    
            elif consts.TEXT_UNIT_TABLE in self.data and self.data[consts.TEXT_UNIT_TABLE] is not None:
                # Basic search
                async for chunk in api.basic_search_streaming(
                    config=self.config,
                    text_units=self.data[consts.TEXT_UNIT_TABLE],
                    query=query,
                    callbacks=[callbacks]
                ):
                    yield chunk
                    
            else:
                logger.warning("Missing required data, cannot execute stream search")
                yield "Search engine is not properly configured. Please ensure text data is uploaded and configuration is correct."
                
        except Exception as e:
            logger.error(f"Stream search error: {str(e)}")
            yield f"Error during search: {str(e)}"
    
    # Compatibility with old interface
    async def astream_search(self, query, conversation_history=None, **kwargs):
        """Stream search using GraphRAG API, compatibility with old interface"""
        async for chunk in self.stream_search(query, **kwargs):
            yield chunk
    
    async def asearch(self, query, conversation_history=None, **kwargs):
        """Asynchronous search, compatibility with old interface"""
        result = await self.search(query, **kwargs)
        
        # Compatibility with old interface return format
        class ResponseWrapper:
            def __init__(self, result):
                self.response = result.get("answer", "")
                self.prompt_tokens = 0
                self.completion_tokens = 0
                self.llm_calls = 0
                
        return ResponseWrapper(result)

async def load_local_search_engine(config, data):
    """Load local search engine"""
    try:
        handler = SearchEngineHandler(config, data)
        await handler.set_search_engine("LocalSearch")
        return handler
    except Exception as e:
        logger.error(f"Failed to load local search engine: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

async def load_global_search_engine(config, data):
    """Load global search engine"""
    try:
        handler = SearchEngineHandler(config, data)
        await handler.set_search_engine("GlobalSearch")
        return handler
    except Exception as e:
        logger.error(f"Failed to load global search engine: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

async def load_drift_search_engine(config, data):
    """Load DRIFT search engine"""
    try:
        handler = SearchEngineHandler(config, data)
        await handler.set_search_engine("DRIFTSearch")
        return handler
    except Exception as e:
        logger.error(f"Failed to load DRIFT search engine: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

async def load_basic_search_engine(config, data):
    """Load basic search engine"""
    try:
        handler = SearchEngineHandler(config, data)
        await handler.set_search_engine("BasicSearch")
        return handler
    except Exception as e:
        logger.error(f"Failed to load basic search engine: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
