import os
import logging
from typing import Optional, List, Dict, Any
import json

import pandas as pd
import numpy as np
from graphrag.data_model.entity import Entity
from graphrag.data_model.relationship import Relationship
from graphrag.data_model.text_unit import TextUnit
from graphrag.data_model.community_report import CommunityReport

from graphrag.query.indexer_adapters import read_indexer_relationships, read_indexer_entities, \
    read_indexer_reports, read_indexer_text_units
from webserver.utils import consts

# Debug mode switch - set to False by default for production
# When set to True, enables detailed logging for data access operations
# Can be temporarily enabled for a specific request using enable_debug_for_request()
DEBUG_MODE = False

# Function to temporarily enable debug mode for a single request
def enable_debug_for_request():
    """Temporarily enable debug mode and return the original state"""
    global DEBUG_MODE
    original_debug_mode = DEBUG_MODE
    DEBUG_MODE = True
    return original_debug_mode

# Function to restore debug mode to its original value
def restore_debug_mode(original_mode):
    """Restore debug mode to its original state"""
    global DEBUG_MODE
    DEBUG_MODE = original_mode

logger = logging.getLogger(__name__)

async def get_index_data(input_dir: str, datatype: str, id: Optional[str] = None):
    """Get index data of specified type and ID
    
    Args:
        input_dir: Input directory
        datatype: Data type
        id: Data ID
        
    Returns:
        Data object
    """
    logger.info(f"Getting index data of type {datatype} with id {id} from {input_dir}")
    
    # Add ID debug info only when DEBUG_MODE is enabled
    if DEBUG_MODE:
        logger.info(f"ID type: {type(id)}, ID value: {id}")
    
    # Handle all data types with string ID (no conversion to int)
    if datatype == "documents":
        return await get_document(input_dir, id)
    elif datatype == "sources":
        return await get_source(input_dir, id)
    elif datatype == "entities":
        return await get_entity(input_dir, id)
    # Covariates feature removed in GraphRAG 2.1.0
    # elif datatype == "claims":
    #     return await get_claim(input_dir, id)
    elif datatype == "reports":
        return await get_report(input_dir, id)
    elif datatype == "relationships":
        return await get_relationship(input_dir, id)
    else:
        raise ValueError(f"Unknown datatype: {datatype}")


def custom_read_entities(entity_df: pd.DataFrame) -> List[Entity]:
    """Create entity list directly from entity DataFrame without relying on entity_ids field in communities table
    
    Parameters:
        entity_df: Entity DataFrame
        
    Returns:
        List of entity objects
    """
    if DEBUG_MODE:
        logger.info(f"Using custom entity adapter with columns: {entity_df.columns.tolist()}")
    entities = []
    
    try:
        # Check required fields
        required_fields = ['id']
        for field in required_fields:
            if field not in entity_df.columns:
                logger.warning(f"Required field '{field}' missing from entity DataFrame")
                return []
                
        # Process each row
        for idx, row in entity_df.iterrows():
            try:
                # Create basic attributes - only include fields supported by GraphRAG 2.1.0 Entity class
                entity_dict = {
                    "id": str(row["id"]),
                    "short_id": str(idx if "short_id" not in row else row["short_id"]),
                    "title": row["title"] if "title" in row else f"Entity {row['id']}",
                    "type": row["type"] if "type" in row else "entity",
                    "description": ""  # Default empty description
                }
                
                # Safely add description field, handling potential arrays or None
                if "description" in row:
                    desc_value = row["description"]
                    if isinstance(desc_value, (list, np.ndarray)) or (hasattr(desc_value, 'dtype') and pd.api.types.is_array_like(desc_value)):
                        # For array types, add if not all NaN
                        if not pd.isna(desc_value).all():
                            entity_dict["description"] = str(desc_value)
                    elif not pd.isna(desc_value):
                        entity_dict["description"] = str(desc_value)
                
                # Add optional but valid attributes - human_readable_id removed in GraphRAG 2.1.0
                valid_optional_fields = ['text_unit_ids']
                for field in valid_optional_fields:
                    if field in row:
                        # Safely check for NaN, handling array cases
                        field_value = row[field]
                        if isinstance(field_value, (list, np.ndarray)) or (hasattr(field_value, 'dtype') and pd.api.types.is_array_like(field_value)):
                            # For array types, add if not all NaN
                            if not pd.isna(field_value).all():
                                entity_dict[field] = field_value
                        elif not pd.isna(field_value):
                            # For single values, add if not NaN
                            entity_dict[field] = field_value
                
                # Create entity object and add to list
                if DEBUG_MODE:
                    logger.info(f"Creating entity with attributes: {list(entity_dict.keys())}")
                entity = Entity(**entity_dict)
                entities.append(entity)
            except Exception as e:
                logger.error(f"Error processing entity row {idx}: {str(e)}", exc_info=True)
                continue
                
        if DEBUG_MODE:
            logger.info(f"Custom adapter created {len(entities)} entities")
        return entities
    except Exception as e:
        logger.error(f"Error in custom entity adapter: {str(e)}", exc_info=True)
        return []


async def debug_entity_ids(input_dir: str) -> List[str]:
    """Debug function to find all available entity IDs
    
    Parameters:
        input_dir: Input directory
        
    Returns:
        List of entity IDs
    """
    # Skip entire function execution if DEBUG_MODE is disabled
    if not DEBUG_MODE:
        return []
        
    try:
        entity_path = os.path.join(input_dir, f"{consts.ENTITY_TABLE}.parquet")
        logger.info(f"Loading entity data from {entity_path} for debugging")
        
        entity_df = pd.read_parquet(entity_path)
        
        # Log columns and data volume
        logger.info(f"Entity DataFrame has {len(entity_df)} rows and columns: {entity_df.columns.tolist()}")
        
        # Collect all possible IDs
        all_ids = []
        
        # Collect from ID column
        if 'id' in entity_df.columns:
            ids_from_id = entity_df['id'].astype(str).tolist()
            logger.info(f"Found {len(ids_from_id)} IDs from 'id' column")
            all_ids.extend(ids_from_id)
        
        # Collect from short_id column
        if 'short_id' in entity_df.columns:
            ids_from_short_id = entity_df['short_id'].astype(str).tolist()
            logger.info(f"Found {len(ids_from_short_id)} IDs from 'short_id' column")
            all_ids.extend(ids_from_short_id)
            
        # Check if specific ID exists
        target_id = "548"
        if 'id' in entity_df.columns:
            matches = entity_df[entity_df['id'].astype(str) == target_id]
            logger.info(f"Found {len(matches)} matches for ID={target_id} in 'id' column")
            if len(matches) > 0:
                logger.info(f"First match: {matches.iloc[0].to_dict()}")
                
        if 'short_id' in entity_df.columns:
            matches = entity_df[entity_df['short_id'].astype(str) == target_id]
            logger.info(f"Found {len(matches)} matches for ID={target_id} in 'short_id' column")
            if len(matches) > 0:
                logger.info(f"First match: {matches.iloc[0].to_dict()}")
        
        # Check numeric type matching
        try:
            target_id_int = int(target_id)
            if 'id' in entity_df.columns:
                # Try converting ID column to integer for matching
                if entity_df['id'].dtype == 'int64' or entity_df['id'].dtype == 'int32':
                    matches = entity_df[entity_df['id'] == target_id_int]
                    logger.info(f"Found {len(matches)} matches for ID={target_id_int} (int) in 'id' column")
                    if len(matches) > 0:
                        logger.info(f"First match: {matches.iloc[0].to_dict()}")
        except (ValueError, TypeError):
            pass
            
        return all_ids
        
    except Exception as e:
        logger.error(f"Error in debug_entity_ids: {str(e)}", exc_info=True)
        return []


async def get_entity(input_dir: str, id: Optional[str] = None) -> Entity:
    """Get entity data
    
    In GraphRAG 2.1.0, entity and embedding information are merged into a single file
    """
    entity_path = os.path.join(input_dir, f"{consts.ENTITY_TABLE}.parquet")
    logger.info(f"Loading entity data from {entity_path}")
    
    try:
        entity_df = pd.read_parquet(entity_path)
        
        # Add debug logs only when DEBUG_MODE is enabled
        if DEBUG_MODE:
            logger.info(f"Looking for entity with ID={id}")
            # Run debug function
            await debug_entity_ids(input_dir)
            
            # Debug: Log entity DataFrame columns
            logger.info(f"Entity DataFrame columns: {entity_df.columns.tolist()}")
            # Debug: Log first few rows for structure
            logger.info(f"Sample entity data (first row): {entity_df.iloc[0].to_dict() if len(entity_df) > 0 else 'Empty DataFrame'}")
        
        # Check if specified ID exists
        if 'id' in entity_df.columns:
            # Try different ID format matches
            matching_rows = pd.DataFrame()
            
            # String matching
            string_matches = entity_df[entity_df['id'].astype(str) == str(id)]
            if not string_matches.empty:
                matching_rows = string_matches
                if DEBUG_MODE:
                    logger.info(f"Found {len(matching_rows)} matches with string comparison for ID={id}")
            
            # If still no match, try integer matching
            if matching_rows.empty:
                try:
                    int_id = int(id)
                    if entity_df['id'].dtype == 'int64' or entity_df['id'].dtype == 'int32':
                        int_matches = entity_df[entity_df['id'] == int_id]
                        if not int_matches.empty:
                            matching_rows = int_matches
                            if DEBUG_MODE:
                                logger.info(f"Found {len(matching_rows)} matches with integer comparison for ID={id}")
                except (ValueError, TypeError):
                    pass
            
            # If no match found, try using short_id
            if matching_rows.empty and 'short_id' in entity_df.columns:
                # String matching
                short_id_matches = entity_df[entity_df['short_id'].astype(str) == str(id)]
                if not short_id_matches.empty:
                    matching_rows = short_id_matches
                    if DEBUG_MODE:
                        logger.info(f"Found {len(matching_rows)} matches with string comparison for short_id={id}")
                
                # If still no match, try integer matching
                if matching_rows.empty:
                    try:
                        int_id = int(id)
                        if entity_df['short_id'].dtype == 'int64' or entity_df['short_id'].dtype == 'int32':
                            int_matches = entity_df[entity_df['short_id'] == int_id]
                            if not int_matches.empty:
                                matching_rows = int_matches
                                if DEBUG_MODE:
                                    logger.info(f"Found {len(matching_rows)} matches with integer comparison for short_id={id}")
                    except (ValueError, TypeError):
                        pass
            
            # If still not found, try other possible ID columns
            if matching_rows.empty:
                for col in entity_df.columns:
                    if 'id' in col.lower() and col not in ['id', 'short_id']:
                        try:
                            potential_matches = entity_df[entity_df[col].astype(str) == str(id)]
                            if not potential_matches.empty:
                                matching_rows = potential_matches
                                if DEBUG_MODE:
                                    logger.info(f"Found {len(matching_rows)} matches in column {col} for ID={id}")
                                break
                        except:
                            continue
            
            if not matching_rows.empty:
                # Found matching record, construct entity directly from DataFrame
                row = matching_rows.iloc[0]
                if DEBUG_MODE:
                    logger.info(f"Found matching entity with id={id}")
                
                # In GraphRAG 2.1.0, Entity class only accepts the following parameters
                # Create entity attribute dictionary, only including columns supported by GraphRAG 2.1.0 Entity class
                entity_attrs = {
                    'id': str(row['id']),
                    'short_id': str(id),
                    'title': row['title'] if 'title' in row else "No Title",
                    'description': row['description'] if 'description' in row else "",
                    'type': row['type'] if 'type' in row else "unknown"
                }
                
                # Only add fields supported by Entity class (GraphRAG 2.1.0)
                # Note: human_readable_id is also not supported
                valid_optional_fields = ['text_unit_ids']
                for field in valid_optional_fields:
                    if field in row:
                        # Safely check for NaN, handling array cases
                        field_value = row[field]
                        if isinstance(field_value, (list, np.ndarray)) or (hasattr(field_value, 'dtype') and pd.api.types.is_array_like(field_value)):
                            # For array types, add if not all NaN
                            if not pd.isna(field_value).all():
                                entity_attrs[field] = field_value
                        elif not pd.isna(field_value):
                            # For single values, add if not NaN
                            entity_attrs[field] = field_value
                
                if DEBUG_MODE:
                    logger.info(f"Creating Entity with attributes: {list(entity_attrs.keys())}")
                return Entity(**entity_attrs)
            else:
                logger.warning(f"Could not find entity with id={id} using direct DataFrame lookup")
                
                # If no match found, try logging some entity ID examples
                if DEBUG_MODE:
                    sample_ids = []
                    if 'id' in entity_df.columns:
                        sample_ids = entity_df['id'].astype(str).head(5).tolist()
                    logger.info(f"Sample entity IDs: {sample_ids}")
        
        # If direct method above doesn't work, try safely using adapter
        try:
            if DEBUG_MODE:
                logger.info("Attempting to use adapter function")
            # First try custom adapter function
            entities = custom_read_entities(entity_df)
            
            if not entities:
                # If custom adapter fails, try official adapter function
                try:
                    if DEBUG_MODE:
                        logger.info("Custom adapter returned no entities, trying official adapter")
                    entities = read_indexer_entities(entity_df, entity_df, consts.COMMUNITY_LEVEL)
                except KeyError as key_error:
                    # If it's a key error (e.g., entity_ids), log and use custom adapter
                    if 'entity_ids' in str(key_error):
                        logger.warning(f"Official adapter failed with KeyError: {key_error}. This is expected if 'entity_ids' is missing.")
                        # Already tried custom adapter, no need to try again
                    else:
                        # Other key errors, raise up
                        raise
                    
            # Regardless of which adapter is used, find matching entity
            for entity in entities:
                if int(entity.short_id) == int(id):
                    if DEBUG_MODE:
                        logger.info(f"Found entity with adapter, id={id}")
                    return entity
                    
            # If still not found, try other possible matches
            for entity in entities:
                if str(entity.id) == str(id):
                    if DEBUG_MODE:
                        logger.info(f"Found entity by matching ID field instead of short_id, id={id}")
                    return entity
                    
        except Exception as adapter_error:
            logger.error(f"Error in adapter function: {str(adapter_error)}", exc_info=True)
            
            # If adapter method fails, try constructing basic entity object directly from raw data
            if len(entity_df) > 0:
                for _, row in entity_df.iterrows():
                    # Use various possible matching methods
                    potential_id_fields = ['id', 'short_id', 'entity_id']
                    for id_field in potential_id_fields:
                        if id_field in row and str(row[id_field]) == str(id):
                            if DEBUG_MODE:
                                logger.info(f"Found entity using fallback method with {id_field}={id}")
                            
                            # Create basic object, use only valid fields
                            return Entity(
                                id=str(row['id']) if 'id' in row else str(id),
                                short_id=str(id),
                                title=row['title'] if 'title' in row else str(id),
                                description=row.get('description', ""),
                                type=row.get('type', "entity")
                            )
                
                # If still not found, create default object
                logger.warning(f"Falling back to a default entity with data from first row")
                first_row = entity_df.iloc[0]
                return Entity(
                    id="not_found",
                    short_id=str(id),
                    title=f"Entity {id} (Data available but not matched)",
                    description="Entity data could not be matched by ID but data exists",
                    type="unknown"
                )
        
        # If execution reaches here, it means the entity truly doesn't exist
        raise ValueError(f"Not Found entity id {id}")
    except Exception as e:
        logger.error(f"Error loading entity: {str(e)}", exc_info=True)
        # Return an empty entity object to avoid page crash
        return Entity(
            id="error",
            short_id="0",
            title=f"Error: {str(e)}",
            description="Could not load entity data. Check server logs for details.",
            type="error"
        )


# Covariates feature removed in GraphRAG 2.1.0
"""
async def get_claim(input_dir: str, row_id: Optional[int] = None) -> Covariate:
    # This functionality was removed in GraphRAG 2.1.0
    raise ValueError(f"Claims functionality removed in GraphRAG 2.1.0")
"""


async def get_source(input_dir: str, id: Optional[str] = None) -> TextUnit:
    """Get text unit data"""
    source_path = os.path.join(input_dir, f"{consts.TEXT_UNIT_TABLE}.parquet")
    logger.info(f"Loading source data from {source_path}")
    
    try:
        text_unit_df = pd.read_parquet(source_path)
        
        # Debug: Log DataFrame columns
        if DEBUG_MODE:
            logger.info(f"Text Unit DataFrame columns: {text_unit_df.columns.tolist()}")
            logger.info(f"Sample text unit data (first row): {text_unit_df.iloc[0].to_dict() if len(text_unit_df) > 0 else 'Empty DataFrame'}")
            logger.info(f"Looking for text unit with ID type: {type(id)}, value: {id}")
        
        # Check if specified ID exists
        if 'id' in text_unit_df.columns:
            # Try exact match first - compare as strings to handle hash IDs
            id_matches = (text_unit_df['id'].astype(str) == str(id))
            matching_rows = text_unit_df[id_matches]
            
            if DEBUG_MODE and not matching_rows.empty:
                logger.info(f"Found {len(matching_rows)} matches for ID={id}")
            
            # If no exact match, try matching where short_id might be
            if matching_rows.empty and 'short_id' in text_unit_df.columns:
                short_id_matches = (text_unit_df['short_id'].astype(str) == str(id))
                matching_rows = text_unit_df[short_id_matches]
                if DEBUG_MODE:
                    logger.info(f"Tried matching by short_id, found: {len(matching_rows)} rows")
            
            if not matching_rows.empty:
                # Found matching record, construct TextUnit directly from DataFrame
                row = matching_rows.iloc[0]
                if DEBUG_MODE:
                    logger.info(f"Found matching text unit with id={id}")
                
                # Create TextUnit attribute dictionary with existing columns
                text_unit_attrs = {
                    'id': str(row['id']),
                    'short_id': str(id),
                    'text': row['text'] if 'text' in row else "No Text"
                }
                
                # Note: 'file' parameter removed in GraphRAG 2.1.0
                
                # Add optional fields - with array check fix
                for field in ['n_tokens', 'document_ids', 'entity_ids', 'relationship_ids', 'covariate_ids']:
                    if field in row:
                        # Safely check for NaN, handling array cases
                        field_value = row[field]
                        if isinstance(field_value, (list, np.ndarray)) or (hasattr(field_value, 'dtype') and pd.api.types.is_array_like(field_value)):
                            # For array types, add if not all NaN
                            if not pd.isna(field_value).all():
                                text_unit_attrs[field] = field_value
                        elif not pd.isna(field_value):
                            # For single values, add if not NaN
                            text_unit_attrs[field] = field_value
                
                return TextUnit(**text_unit_attrs)
            else:
                logger.warning(f"Could not find text unit with id={id} using direct DataFrame lookup")
        
        # If direct method above doesn't work, try safely using adapter
        try:
            if DEBUG_MODE:
                logger.info("Attempting to use adapter function")
            text_units = read_indexer_text_units(text_unit_df)
            
            # Check if text_units is None or empty before iterating
            if text_units:
                # First try to match by string ID (for hash IDs)
                for text_unit in text_units:
                    if str(text_unit.id) == str(id):
                        if DEBUG_MODE:
                            logger.info(f"Found text unit by matching ID field, id={id}")
                        return text_unit
                
                # Then try short_id for backward compatibility with integer IDs
                for text_unit in text_units:
                    try:
                        if int(text_unit.short_id) == int(id):
                            if DEBUG_MODE:
                                logger.info(f"Found text unit with adapter using short_id, id={id}")
                            return text_unit
                    except (ValueError, TypeError):
                        # Skip comparison if IDs can't be converted to int
                        pass
            elif DEBUG_MODE:
                logger.warning("Adapter function returned None or empty list")
                    
        except Exception as adapter_error:
            logger.error(f"Error in adapter function: {str(adapter_error)}", exc_info=True)
            
            # If adapter method fails, try constructing basic TextUnit object directly from raw data
            if len(text_unit_df) > 0:
                for _, row in text_unit_df.iterrows():
                    # Use various possible matching methods
                    potential_id_fields = ['id', 'short_id', 'text_unit_id']
                    for id_field in potential_id_fields:
                        if id_field in row and str(row[id_field]) == str(id):
                            if DEBUG_MODE:
                                logger.info(f"Found text unit using fallback method with {id_field}={id}")
                            
                            # Create basic object without 'file' parameter (removed in GraphRAG 2.1.0)
                            return TextUnit(
                                id=str(row['id']) if 'id' in row else str(id),
                                short_id=str(id),
                                text=row['text'] if 'text' in row else f"Text unit {id}"
                            )
                
                # If still not found, create default object
                logger.warning(f"Falling back to a default text unit with data from first row")
                return TextUnit(
                    id="not_found",
                    short_id=str(id),
                    text=f"Text unit {id} (Data available but not matched)"
                )
        
        # If execution reaches here, it means the text unit truly doesn't exist
        raise ValueError(f"Not Found source id {id}")
    except Exception as e:
        logger.error(f"Error loading source: {str(e)}", exc_info=True)
        # Return an empty text unit object to avoid page crash
        return TextUnit(
            id="error",
            short_id="0",
            text=f"Error: {str(e)}\nCould not load source data. Check server logs for details."
        )


async def get_report(input_dir: str, id: Optional[str] = None) -> CommunityReport:
    """Get community report data"""
    try:
        report_path = os.path.join(input_dir, f"{consts.COMMUNITY_REPORT_TABLE}.parquet")
        logger.info(f"Loading report data from {report_path}")
        
        report_df = pd.read_parquet(report_path)
        
        # Debug: Log DataFrame columns and detailed info about IDs
        if DEBUG_MODE:
            logger.info(f"Report DataFrame columns: {report_df.columns.tolist()}")
            logger.info(f"Report DataFrame has {len(report_df)} rows")
            logger.info(f"Sample report data (first row): {report_df.iloc[0].to_dict() if len(report_df) > 0 else 'Empty DataFrame'}")
            logger.info(f"ID column type: {report_df['id'].dtype if 'id' in report_df.columns else 'no id column'}")
            if 'id' in report_df.columns:
                sample_ids = report_df['id'].head(10).tolist()
                logger.info(f"Sample IDs in dataframe: {sample_ids}")
            logger.info(f"Looking for report with ID type: {type(id)}, value: {id}")
        
        # Check if specified ID exists
        if 'id' in report_df.columns:
            # Try multiple matching strategies
            matching_rows = pd.DataFrame()
            
            # Method 1: Direct string matching (most reliable across types)
            string_match = report_df[report_df['id'].astype(str) == str(id)]
            if not string_match.empty:
                matching_rows = string_match
                if DEBUG_MODE:
                    logger.info(f"Found {len(matching_rows)} matches using string comparison for ID={id}")
            
            # Method 2: Try integer matching if possible
            if matching_rows.empty:
                try:
                    int_id = int(id)
                    if report_df['id'].dtype == 'int64' or report_df['id'].dtype == 'int32':
                        int_match = report_df[report_df['id'] == int_id]
                        if not int_match.empty:
                            matching_rows = int_match
                            if DEBUG_MODE:
                                logger.info(f"Found {len(matching_rows)} matches using integer comparison for ID={id}")
                except (ValueError, TypeError):
                    pass
            
            # Method 3: Try using short_id if it exists
            if matching_rows.empty and 'short_id' in report_df.columns:
                short_id_match = report_df[report_df['short_id'].astype(str) == str(id)]
                if not short_id_match.empty:
                    matching_rows = short_id_match
                    if DEBUG_MODE:
                        logger.info(f"Found {len(matching_rows)} matches using short_id={id}")
            
            # Method 4: Try human_readable_id if it exists
            if matching_rows.empty and 'human_readable_id' in report_df.columns:
                human_id_match = report_df[report_df['human_readable_id'].astype(str) == str(id)]
                if not human_id_match.empty:
                    matching_rows = human_id_match
                    if DEBUG_MODE:
                        logger.info(f"Found {len(matching_rows)} matches using human_readable_id={id}")
            
            # Last resort: Look for any integer index matching the row_id (position-based fallback)
            if matching_rows.empty and isinstance(id, int) and id < len(report_df):
                # Try to use row_id as a positional index
                if DEBUG_MODE:
                    logger.info(f"Attempting to use row_id={id} as a positional index")
                try:
                    matching_rows = report_df.iloc[[id]]
                    if DEBUG_MODE:
                        logger.info(f"Found match using row_id={id} as positional index")
                except IndexError:
                    pass
            
            if not matching_rows.empty:
                # Found matching record, construct CommunityReport directly from DataFrame
                row = matching_rows.iloc[0]
                if DEBUG_MODE:
                    logger.info(f"Found matching report with id={id}")
                    logger.info(f"Matched row data: {row.to_dict()}")
                
                # Create CommunityReport attribute dictionary with required columns
                report_dict = {
                    "id": str(row['id']),
                    "short_id": str(id),
                    "community_id": str(row['community']) if 'community' in row else "",
                    "summary": "",  # Default empty summary
                    "title": row.get("title", f"Report {row['id']}") if not pd.isna(row.get("title", "")) else f"Report {row['id']}",  # Default title
                    "attributes": {}  # Required in GraphRAG 2.1.0
                }
                
                # Safely add summary field, handling potential arrays or None
                if "summary" in row:
                    summary_value = row["summary"]
                    if isinstance(summary_value, (list, np.ndarray)) or (hasattr(summary_value, 'dtype') and pd.api.types.is_array_like(summary_value)):
                        # For array types, add if not all NaN
                        if not pd.isna(summary_value).all():
                            report_dict["summary"] = str(summary_value)
                    elif not pd.isna(summary_value):
                        report_dict["summary"] = str(summary_value)
                
                # Add optional fields - only those supported by CommunityReport in GraphRAG 2.1.0
                for field in ['full_content', 'rank', 'size', 'period']:
                    if field in row:
                        # Safely check for NaN, handling array cases
                        field_value = row[field]
                        if isinstance(field_value, (list, np.ndarray)) or (hasattr(field_value, 'dtype') and pd.api.types.is_array_like(field_value)):
                            # For array types, add if not all NaN
                            if not pd.isna(field_value).all():
                                report_dict[field] = field_value
                        elif not pd.isna(field_value):
                            # For single values, add if not NaN
                            report_dict[field] = field_value
                
                # Debug information to help diagnose issues
                if DEBUG_MODE:
                    logger.info(f"Creating CommunityReport with attributes: {list(report_dict.keys())}")
                    
                    # Temporarily try to introspect the CommunityReport class to see accepted parameters
                    try:
                        import inspect
                        from graphrag.data_model.community_report import CommunityReport as CR
                        init_params = list(inspect.signature(CR.__init__).parameters.keys())
                        # Remove 'self' from the list
                        if 'self' in init_params:
                            init_params.remove('self')
                        logger.info(f"CommunityReport.__init__ accepts these parameters: {init_params}")
                    except Exception as inspect_err:
                        logger.error(f"Failed to inspect CommunityReport: {inspect_err}")
                
                return CommunityReport(**report_dict)
            else:
                logger.warning(f"Could not find report with id={id} using direct DataFrame lookup")
                if DEBUG_MODE:
                    # Print some sample IDs to help diagnose the issue
                    if 'id' in report_df.columns:
                        sample_ids = report_df['id'].astype(str).head(5).tolist()
                        logger.info(f"Sample report IDs available: {sample_ids}")
                    # Print all column values for the first row as a reference
                    if len(report_df) > 0:
                        logger.info(f"Example row data structure: {report_df.iloc[0].to_dict()}")
        
        # If direct method above doesn't work, try safely using adapter
        try:
            if DEBUG_MODE:
                logger.info("Attempting to use adapter function")
            reports = read_indexer_reports(report_df)
            
            for report in reports:
                if int(report.short_id) == int(id):
                    if DEBUG_MODE:
                        logger.info(f"Found report with adapter, id={id}")
                    return report
                    
            # If still not found, try other possible matches
            for report in reports:
                if str(report.id) == str(id):
                    if DEBUG_MODE:
                        logger.info(f"Found report by matching ID field instead of short_id, id={id}")
                    return report
                
        except Exception as adapter_error:
            logger.error(f"Error in adapter function: {str(adapter_error)}", exc_info=True)
            
            # If adapter method fails, try constructing basic CommunityReport object directly from raw data
            if len(report_df) > 0:
                for _, row in report_df.iterrows():
                    # Use various possible matching methods
                    potential_id_fields = ['id', 'short_id', 'report_id']
                    for id_field in potential_id_fields:
                        if id_field in row and str(row[id_field]) == str(id):
                            if DEBUG_MODE:
                                logger.info(f"Found report using fallback method with {id_field}={id}")
                            
                            # Create basic object
                            return CommunityReport(
                                id=str(row['id']) if 'id' in row else str(id),
                                short_id=str(id),
                                community_id=str(row['community']) if 'community' in row else "",
                                summary=row['summary'] if 'summary' in row and not pd.isna(row['summary']) else f"Report {id}",
                                title=f"Report {id}",
                                attributes={}
                            )
                
                # If still not found, create default object
                logger.warning(f"Falling back to a default report with data from first row")
                return CommunityReport(
                    id="not_found",
                    short_id=str(id),
                    community_id="unknown",
                    summary=f"Report {id} (Data available but not matched)",
                    title=f"Report {id}",
                    attributes={}
                )
        
        # If execution reaches here, it means the report truly doesn't exist
        raise ValueError(f"Not Found report id {id}")
    except Exception as e:
        logger.error(f"Error loading report: {str(e)}", exc_info=True)
        # Return an empty report object to avoid page crash
        return CommunityReport(
            id="error",
            short_id="0",
            community_id="error",
            summary=f"Error: {str(e)}\nCould not load report data. Check server logs for details.",
            title=f"Report {id}",
            attributes={}
        )


async def get_relationship(input_dir: str, id: Optional[str] = None) -> Relationship:
    """Get relationship data"""
    try:
        relationship_path = os.path.join(input_dir, f"{consts.RELATIONSHIP_TABLE}.parquet")
        logger.info(f"Loading relationship data from {relationship_path}")
        
        relationship_df = pd.read_parquet(relationship_path)
        
        # Debug: Log DataFrame columns
        if DEBUG_MODE:
            logger.info(f"Relationship DataFrame columns: {relationship_df.columns.tolist()}")
            logger.info(f"Sample relationship data (first row): {relationship_df.iloc[0].to_dict() if len(relationship_df) > 0 else 'Empty DataFrame'}")
        
        # Check if specified ID exists
        if 'id' in relationship_df.columns:
            # Try exact match first
            matching_rows = relationship_df[relationship_df['id'].astype(str) == str(id)]
            
            # If no exact match, try matching where short_id might be
            if matching_rows.empty and 'short_id' in relationship_df.columns:
                matching_rows = relationship_df[relationship_df['short_id'].astype(str) == str(id)]
                if DEBUG_MODE:
                    logger.info(f"Tried matching by short_id, found: {len(matching_rows)} rows")
            
            if not matching_rows.empty:
                # Found matching record, construct Relationship directly from DataFrame
                row = matching_rows.iloc[0]
                if DEBUG_MODE:
                    logger.info(f"Found matching relationship with id={id}")
                
                # Create Relationship attribute dictionary with required columns
                rel_attrs = {
                    'id': str(row['id']),
                    'short_id': str(id),
                    'source': str(row['source']) if 'source' in row else "unknown",
                    'target': str(row['target']) if 'target' in row else "unknown",
                    'description': row['description'] if 'description' in row and not pd.isna(row['description']) else ""
                }
                
                # Add optional fields - with array check fix
                for field in ['weight', 'text_unit_ids']:
                    if field in row:
                        # Safely check for NaN, handling array cases
                        field_value = row[field]
                        if isinstance(field_value, (list, np.ndarray)) or (hasattr(field_value, 'dtype') and pd.api.types.is_array_like(field_value)):
                            # For array types, add if not all NaN
                            if not pd.isna(field_value).all():
                                rel_attrs[field] = field_value
                        elif not pd.isna(field_value):
                            # For single values, add if not NaN
                            rel_attrs[field] = field_value
                
                return Relationship(**rel_attrs)
            else:
                logger.warning(f"Could not find relationship with id={id} using direct DataFrame lookup")
        
        # If direct method above doesn't work, try safely using adapter
        try:
            if DEBUG_MODE:
                logger.info("Attempting to use adapter function")
            relationships = read_indexer_relationships(relationship_df)
            
            for relationship in relationships:
                if int(relationship.short_id) == int(id):
                    if DEBUG_MODE:
                        logger.info(f"Found relationship with adapter, id={id}")
                    return relationship
                    
            # If still not found, try other possible matches
            for relationship in relationships:
                if str(relationship.id) == str(id):
                    if DEBUG_MODE:
                        logger.info(f"Found relationship by matching ID field instead of short_id, id={id}")
                    return relationship
                
        except Exception as adapter_error:
            logger.error(f"Error in adapter function: {str(adapter_error)}", exc_info=True)
            
            # If adapter method fails, try constructing basic Relationship object directly from raw data
            if len(relationship_df) > 0:
                for _, row in relationship_df.iterrows():
                    # Use various possible matching methods
                    potential_id_fields = ['id', 'short_id', 'relationship_id']
                    for id_field in potential_id_fields:
                        if id_field in row and str(row[id_field]) == str(id):
                            if DEBUG_MODE:
                                logger.info(f"Found relationship using fallback method with {id_field}={id}")
                            
                            # Create basic object
                            return Relationship(
                                id=str(row['id']) if 'id' in row else str(id),
                                short_id=str(id),
                                source=str(row['source']) if 'source' in row else "unknown",
                                target=str(row['target']) if 'target' in row else "unknown",
                                description=row.get('description', ""),
                                weight=row.get('weight', 0.0)
                            )
                
                # If still not found, create default object
                logger.warning(f"Falling back to a default relationship with data from first row")
                return Relationship(
                    id="not_found",
                    short_id=str(id),
                    source="unknown",
                    target="unknown",
                    description=f"Relationship {id} (Data available but not matched)",
                    weight=0.0
                )
        
        # If execution reaches here, it means the relationship truly doesn't exist
        raise ValueError(f"Not Found relationship id {id}")
    except Exception as e:
        logger.error(f"Error loading relationship: {str(e)}", exc_info=True)
        # Return an empty relationship object to avoid page crash
        return Relationship(
            id="error",
            short_id="0",
            source="error",
            target="error",
            description=f"Error: {str(e)}\nCould not load relationship data. Check server logs for details.",
            weight=0.0
        )


def read_community_reports(reports_df: pd.DataFrame) -> List[CommunityReport]:
    """Read community reports from DataFrame"""
    try:
        reports = []
        if reports_df.empty:
            logger.warning("Reports DataFrame is empty")
            return []
            
        if DEBUG_MODE:
            logger.info(f"Reading community reports with columns: {reports_df.columns.tolist()}")
            
        for idx, row in reports_df.iterrows():
            try:
                if DEBUG_MODE:
                    logger.info(f"Processing report row {idx} with ID: {row.get('id', 'N/A')}")
                    
                report_dict = {
                    "id": str(row["id"]),
                    "short_id": str(row["id"]),
                    "community_id": str(row["community"]) if "community" in row else "",
                    "summary": "",  # Default empty summary
                    "title": row.get("title", f"Report {row['id']}") if not pd.isna(row.get("title", "")) else f"Report {row['id']}",  # Default title
                    "attributes": {}  # Required in GraphRAG 2.1.0
                }
                
                # Safely add summary field, handling potential arrays or None
                if "summary" in row:
                    summary_value = row["summary"]
                    if isinstance(summary_value, (list, np.ndarray)) or (hasattr(summary_value, 'dtype') and pd.api.types.is_array_like(summary_value)):
                        # For array types, add if not all NaN
                        if not pd.isna(summary_value).all():
                            report_dict["summary"] = str(summary_value)
                    elif not pd.isna(summary_value):
                        report_dict["summary"] = str(summary_value)
                
                # Add optional fields - only those supported by CommunityReport in GraphRAG 2.1.0
                for field in ['full_content', 'rank', 'size', 'period']:
                    if field in row:
                        # Safely check for NaN, handling array cases
                        field_value = row[field]
                        if isinstance(field_value, (list, np.ndarray)) or (hasattr(field_value, 'dtype') and pd.api.types.is_array_like(field_value)):
                            # For array types, add if not all NaN
                            if not pd.isna(field_value).all():
                                report_dict[field] = field_value
                        elif not pd.isna(field_value):
                            # For single values, add if not NaN
                            report_dict[field] = field_value
                
                if DEBUG_MODE:
                    logger.info(f"Creating report with attributes: {list(report_dict.keys())}")
                report = CommunityReport(**report_dict)
                reports.append(report)
            except Exception as e:
                logger.error(f"Error processing report row: {str(e)}", exc_info=True)
                continue
                
        if DEBUG_MODE:
            logger.info(f"Successfully created {len(reports)} community reports")
        return reports
    except Exception as e:
        logger.error(f"Error reading community reports: {str(e)}", exc_info=True)
        return []


async def get_document(input_dir: str, id: Optional[str] = None) -> Dict[str, Any]:
    """Get document data"""
    document_path = os.path.join(input_dir, f"{consts.DOCUMENT_TABLE}.parquet")
    logger.info(f"Loading document data from {document_path}")
    
    try:
        document_df = pd.read_parquet(document_path)
        
        # Debug: Log DataFrame columns
        if DEBUG_MODE:
            logger.info(f"Document DataFrame columns: {document_df.columns.tolist()}")
            logger.info(f"Sample document data (first row): {document_df.iloc[0].to_dict() if len(document_df) > 0 else 'Empty DataFrame'}")
            logger.info(f"Looking for document with ID type: {type(id)}, value: {id}")
        
        # Check if specified ID exists
        if 'id' in document_df.columns:
            # Try exact string match - this works for both integer and string IDs
            # Convert both sides to string for comparison
            id_matches = (document_df['id'].astype(str) == str(id))
            matching_rows = document_df[id_matches]
            
            if not matching_rows.empty:
                # Found matching record, create document data directly from DataFrame
                row = matching_rows.iloc[0]
                if DEBUG_MODE:
                    logger.info(f"Found matching document with id={id}")
                
                # Create document data dictionary with all fields
                document_data = {
                    'id': str(row['id']),
                    'short_id': str(id)  # Use id as short_id for consistency
                }
                
                # Add all available fields from dataframe
                for field in ['human_readable_id', 'title', 'text', 'text_unit_ids', 'creation_date', 'metadata']:
                    if field in row:
                        # Handle arrays and NaN values properly
                        field_value = row[field]
                        
                        # Check if it's an array-like object
                        if isinstance(field_value, (list, np.ndarray)) or (hasattr(field_value, 'dtype') and pd.api.types.is_array_like(field_value)):
                            # For arrays, check if all values are NaN
                            if pd.isna(field_value).all():
                                # Skip this field if all values are NaN
                                continue
                            else:
                                # Include the field with array values
                                document_data[field] = field_value
                        # For non-array values, just check if it's NaN
                        elif not pd.isna(field_value):
                            # Handle metadata specially
                            if field == 'metadata' and isinstance(field_value, (dict, str)):
                                # Format metadata as JSON if it's a dict or string
                                if isinstance(field_value, dict):
                                    document_data[field] = json.dumps(field_value, indent=2)
                                else:
                                    # Try to parse as JSON if it's a string
                                    try:
                                        metadata_dict = json.loads(field_value)
                                        document_data[field] = json.dumps(metadata_dict, indent=2)
                                    except:
                                        document_data[field] = str(field_value)
                            else:
                                document_data[field] = field_value
                
                return document_data
            else:
                logger.warning(f"Could not find document with id={id}")
                return {
                    'id': 'not_found',
                    'short_id': str(id),
                    'title': f"Document {id}",
                    'text': f"Document with ID {id} not found in the database."
                }
        else:
            logger.warning(f"Document DataFrame does not have 'id' column")
            return {
                'id': 'error',
                'short_id': str(id),
                'title': 'Error: Invalid Document Data',
                'text': 'The document data does not have the expected structure.'
            }
    except Exception as e:
        logger.error(f"Error loading document: {str(e)}", exc_info=True)
        return {
            'id': 'error',
            'short_id': '0',
            'title': f"Error: {str(e)}",
            'text': f"Could not load document data. Check server logs for details."
        }
