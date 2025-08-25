"""Dataset management functions."""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from .models import DatasetMetadata, DataFile, get_model_version


class DatasetManager:
    """Manages dataset registration and metadata."""
    
    def __init__(self, default_country: Optional[str] = None):
        """Initialize dataset manager.
        
        Args:
            default_country: Default country to use when not specified
        """
        self.default_country = default_country
    
    def create_datafile(
        self,
        session: Session,
        filename: str,
        local_path: str = None,
        gcs_bucket: str = None,
        gcs_path: str = None,
        huggingface_repo: str = None,
        huggingface_path: str = None,
        file_size_mb: float = None,
        checksum: str = None,
    ) -> DataFile:
        """Create a DataFile entry.
        
        Args:
            session: Database session
            filename: Name of the file
            local_path: Local file path
            gcs_bucket: Google Cloud Storage bucket name
            gcs_path: Path within GCS bucket
            huggingface_repo: HuggingFace repository
            huggingface_path: Path within HuggingFace repo
            file_size_mb: File size in MB
            checksum: File checksum for integrity
            
        Returns:
            Created DataFile object
        """
        datafile = DataFile(
            id=str(uuid.uuid4()),
            filename=filename,
            local_path=local_path,
            gcs_bucket=gcs_bucket,
            gcs_path=gcs_path,
            huggingface_repo=huggingface_repo,
            huggingface_path=huggingface_path,
            file_size_mb=file_size_mb,
            checksum=checksum
        )
        session.add(datafile)
        session.flush()
        return datafile
    
    def add_dataset(
        self,
        session: Session,
        name: str,
        country: str = None,
        year: int = None,
        source: str = None,
        version: str = None,
        description: str = None,
        datafile: DataFile = None,
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
            datafile: Optional DataFile object to link to this dataset
            
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
            if datafile:
                existing.datafile = datafile
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
                description=description,
                datafile=datafile
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