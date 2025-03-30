import os
import logging
from typing import Optional

import pandas as pd
from graphrag.data_model.entity import Entity
from graphrag.data_model.relationship import Relationship
from graphrag.data_model.text_unit import TextUnit
from graphrag.data_model.community_report import CommunityReport

from graphrag.query.indexer_adapters import read_indexer_relationships, read_indexer_entities, \
    read_indexer_reports, read_indexer_text_units
from webserver.utils import consts

logger = logging.getLogger(__name__)

async def get_index_data(input_dir: str, datatype: str, id: Optional[int] = None):
    """Get index data of specified type and ID
    
    Args:
        input_dir: Input directory
        datatype: Data type
        id: Data ID
        
    Returns:
        Data object
    """
    logger.info(f"Getting index data of type {datatype} with id {id} from {input_dir}")
    
    if datatype == "entities":
        return await get_entity(input_dir, id)
    # Covariates feature removed in GraphRAG 2.1.0
    # elif datatype == "claims":
    #     return await get_claim(input_dir, id)
    elif datatype == "sources":
        return await get_source(input_dir, id)
    elif datatype == "reports":
        return await get_report(input_dir, id)
    elif datatype == "relationships":
        return await get_relationship(input_dir, id)
    else:
        raise ValueError(f"Unknown datatype: {datatype}")


async def get_entity(input_dir: str, row_id: Optional[int] = None) -> Entity:
    """Get entity data
    
    In GraphRAG 2.1.0, entity and embedding information are merged into a single file
    """
    entity_path = os.path.join(input_dir, f"{consts.ENTITY_TABLE}.parquet")
    logger.info(f"Loading entity data from {entity_path}")
    
    try:
        entity_df = pd.read_parquet(entity_path)
        
        # Entity and embedding information are merged
        entities = read_indexer_entities(entity_df, entity_df, consts.COMMUNITY_LEVEL)
        for entity in entities:
            if int(entity.short_id) == row_id:
                return entity
        raise ValueError(f"Not Found entity id {row_id}")
    except Exception as e:
        logger.error(f"Error loading entity: {str(e)}")
        # Return an empty entity object to avoid page crash
        return Entity(
            id="error",
            name=f"Error: {str(e)}",
            description="Could not load entity data",
            type="error"
        )


# Covariates feature removed in GraphRAG 2.1.0
"""
async def get_claim(input_dir: str, row_id: Optional[int] = None) -> Covariate:
    # This functionality was removed in GraphRAG 2.1.0
    raise ValueError(f"Claims functionality removed in GraphRAG 2.1.0")
"""


async def get_source(input_dir: str, row_id: Optional[int] = None) -> TextUnit:
    """Get text unit data"""
    source_path = os.path.join(input_dir, f"{consts.TEXT_UNIT_TABLE}.parquet")
    logger.info(f"Loading source data from {source_path}")
    
    try:
        text_unit_df = pd.read_parquet(source_path)
        text_units = read_indexer_text_units(text_unit_df)
        for text_unit in text_units:
            if int(text_unit.short_id) == row_id:
                return text_unit
        raise ValueError(f"Not Found source id {row_id}")
    except Exception as e:
        logger.error(f"Error loading source: {str(e)}")
        # Return an empty text unit object to avoid page crash
        return TextUnit(
            id="error",
            file="error",
            text=f"Error: {str(e)}\nCould not load source data"
        )


async def get_report(input_dir: str, row_id: Optional[int] = None) -> CommunityReport:
    """Get community report data"""
    try:
        entity_path = os.path.join(input_dir, f"{consts.ENTITY_TABLE}.parquet")
        report_path = os.path.join(input_dir, f"{consts.COMMUNITY_REPORT_TABLE}.parquet")
        logger.info(f"Loading report data from {report_path}")
        
        entity_df = pd.read_parquet(entity_path)
        report_df = pd.read_parquet(report_path)
        reports = read_indexer_reports(report_df, entity_df, consts.COMMUNITY_LEVEL)
        for report in reports:
            if int(report.short_id) == row_id:
                return report
        raise ValueError(f"Not Found report id {row_id}")
    except Exception as e:
        logger.error(f"Error loading report: {str(e)}")
        # Return an empty report object to avoid page crash
        return CommunityReport(
            id="error",
            summary=f"Error: {str(e)}\nCould not load report data",
            community_id="error"
        )


async def get_relationship(input_dir: str, row_id: Optional[int] = None) -> Relationship:
    """Get relationship data"""
    try:
        relationship_path = os.path.join(input_dir, f"{consts.RELATIONSHIP_TABLE}.parquet")
        logger.info(f"Loading relationship data from {relationship_path}")
        
        relationship_df = pd.read_parquet(relationship_path)
        relationships = read_indexer_relationships(relationship_df)
        for relationship in relationships:
            if int(relationship.short_id) == row_id:
                return relationship
        raise ValueError(f"Not Found relationship id {row_id}")
    except Exception as e:
        logger.error(f"Error loading relationship: {str(e)}")
        # Return an empty relationship object to avoid page crash
        return Relationship(
            id="error",
            source_id="error",
            target_id="error",
            type=f"Error: {str(e)}",
            description="Could not load relationship data"
        )
