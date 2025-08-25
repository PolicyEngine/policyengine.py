"""Dataset management functions."""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from .models import DatasetMetadata, get_model_version


class DatasetManager:
    """Manages dataset registration and metadata."""
    
    def __init__(self, default_country: Optional[str] = None):
        """Initialize dataset manager.
        
        Args:
            default_country: Default country to use when not specified
        """
        self.default_country = default_country
    
    def add_dataset(
        self,
        session: Session,
        name: str,
        country: str = None,
        year: int = None,
        source: str = None,
        version: str = None,
        description: str = None,
    ) -> DatasetMetadata:
        """Register a dataset in the database.
        
        Args:
            session: Database session
            name: Name of the dataset (e.g., "frs_2023_24")
            country: Country code (uses default if not specified)
            year: Year of the dataset
            source: Source of the dataset (e.g., "FRS", "CPS")
            version: Version of the dataset
            description: Optional description
            
        Returns:
            Created DatasetMetadata object
        """
        country = country or self.default_country
        if not country:
            raise ValueError("Country must be specified or set as default")
        
        if year is None:
            year = datetime.now().year
        
        # Check if dataset already exists
        existing = session.query(DatasetMetadata).filter_by(
            name=name,
            country=country.lower()
        ).first()
        
        if existing:
            # Update existing dataset
            existing.year = year
            existing.source = source or existing.source
            existing.version = version or existing.version
            existing.model_version = get_model_version(country)
            existing.description = description or existing.description
            existing.updated_at = datetime.now()
            dataset = existing
        else:
            # Create new dataset
            dataset = DatasetMetadata(
                id=str(uuid.uuid4()),
                name=name,
                country=country.lower(),
                year=year,
                source=source,
                version=version,
                model_version=get_model_version(country),
                description=description
            )
            session.add(dataset)
        
        session.commit()
        session.refresh(dataset)
        session.expunge(dataset)
        return dataset
    
    def get_dataset(
        self,
        session: Session,
        name: str,
        country: str = None
    ) -> Optional[DatasetMetadata]:
        """Get a dataset by name and country.
        
        Args:
            session: Database session
            name: Name of the dataset
            country: Country code (uses default if not specified)
            
        Returns:
            DatasetMetadata object or None if not found
        """
        country = country or self.default_country
        if not country:
            raise ValueError("Country must be specified or set as default")
        
        dataset = session.query(DatasetMetadata).filter_by(
            name=name,
            country=country.lower()
        ).first()
        
        if dataset:
            session.expunge(dataset)
        
        return dataset
    
    def list_datasets(
        self,
        session: Session,
        country: str = None,
        year: int = None,
        source: str = None
    ) -> List[DatasetMetadata]:
        """List datasets matching criteria.
        
        Args:
            session: Database session
            country: Filter by country
            year: Filter by year
            source: Filter by source
            
        Returns:
            List of DatasetMetadata objects
        """
        query = session.query(DatasetMetadata)
        
        if country:
            query = query.filter_by(country=country.lower())
        elif self.default_country:
            query = query.filter_by(country=self.default_country.lower())
        
        if year:
            query = query.filter_by(year=year)
        
        if source:
            query = query.filter_by(source=source)
        
        datasets = query.order_by(DatasetMetadata.year.desc(), DatasetMetadata.name).all()
        for ds in datasets:
            session.expunge(ds)
        return datasets