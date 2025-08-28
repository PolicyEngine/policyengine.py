"""Storage-agnostic dataset handler.

This module provides business logic for working with datasets using
Pydantic models, independent of storage implementation.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from ..data_models import DatasetModel


class DatasetHandler:
    """Handles dataset operations using Pydantic models."""
    
    @staticmethod
    def create_dataset(
        name: str,
        country: str,
        year: Optional[int] = None,
        source: Optional[str] = None,
        version: Optional[str] = None,
        description: Optional[str] = None,
        model_version: Optional[str] = None,
    ) -> DatasetModel:
        """Create a new dataset model.
        
        Args:
            name: Unique dataset name
            country: Country code
            year: Dataset year
            source: Data source (e.g., 'FRS', 'CPS')
            version: Dataset version
            description: Human-readable description
            model_version: Model version string
            
        Returns:
            DatasetModel instance
        """
        return DatasetModel(
            name=name,
            country=country.lower() if country else "default",
            year=year or datetime.now().year,
            source=source,
            version=version,
            description=description,
            model_version=model_version
        )
    
    @staticmethod
    def get_default_datasets(country: str) -> List[DatasetModel]:
        """Get default datasets for a country.
        
        Args:
            country: Country code
            
        Returns:
            List of default DatasetModel instances
        """
        default_datasets = {
            "uk": [
                DatasetModel(
                    name="frs_2023_24",
                    country="uk",
                    year=2023,
                    source="FRS",
                    description="Family Resources Survey 2023-24"
                ),
                DatasetModel(
                    name="enhanced_frs_2023_24",
                    country="uk",
                    year=2023,
                    source="FRS",
                    description="Enhanced Family Resources Survey 2023-24"
                ),
                DatasetModel(
                    name="synthetic_uk_2023",
                    country="uk",
                    year=2023,
                    source="Synthetic",
                    description="Synthetic UK dataset for testing"
                )
            ],
            "us": [
                DatasetModel(
                    name="cps_2023",
                    country="us",
                    year=2023,
                    source="CPS",
                    description="Current Population Survey 2023"
                ),
                DatasetModel(
                    name="enhanced_cps_2024",
                    country="us",
                    year=2024,
                    source="CPS",
                    description="Enhanced Current Population Survey 2024"
                ),
                DatasetModel(
                    name="synthetic_us_2024",
                    country="us",
                    year=2024,
                    source="Synthetic",
                    description="Synthetic US dataset for testing"
                )
            ]
        }
        
        return default_datasets.get(country.lower(), [])
    
    @staticmethod
    def validate_dataset(dataset: DatasetModel) -> bool:
        """Validate a dataset model.
        
        Args:
            dataset: DatasetModel to validate
            
        Returns:
            True if valid, raises exception otherwise
        """
        if not dataset.name:
            raise ValueError("Dataset must have a name")
        
        if not dataset.country:
            raise ValueError("Dataset must have a country")
        
        if dataset.year and (dataset.year < 1900 or dataset.year > 2100):
            raise ValueError(f"Invalid year: {dataset.year}")
        
        valid_sources = ["FRS", "CPS", "ACS", "SCF", "Synthetic", "Custom", None]
        if dataset.source and dataset.source not in valid_sources:
            raise ValueError(f"Invalid source: {dataset.source}. Must be one of {valid_sources}")
        
        return True
    
    @staticmethod
    def dataset_to_dict(dataset: DatasetModel) -> Dict[str, Any]:
        """Convert dataset to dictionary for serialization.
        
        Args:
            dataset: DatasetModel to convert
            
        Returns:
            Dictionary representation
        """
        return {
            "name": dataset.name,
            "country": dataset.country,
            "year": dataset.year,
            "source": dataset.source,
            "version": dataset.version,
            "description": dataset.description,
            "model_version": dataset.model_version
        }
    
    @staticmethod
    def dataset_from_dict(data: Dict[str, Any]) -> DatasetModel:
        """Create dataset from dictionary.
        
        Args:
            data: Dictionary representation
            
        Returns:
            DatasetModel instance
        """
        return DatasetModel(
            name=data["name"],
            country=data["country"],
            year=data.get("year"),
            source=data.get("source"),
            version=data.get("version"),
            description=data.get("description"),
            model_version=data.get("model_version")
        )
    
    @staticmethod
    def filter_datasets(
        datasets: List[DatasetModel],
        country: Optional[str] = None,
        year: Optional[int] = None,
        source: Optional[str] = None
    ) -> List[DatasetModel]:
        """Filter datasets by criteria.
        
        Args:
            datasets: List of datasets to filter
            country: Filter by country
            year: Filter by year
            source: Filter by source
            
        Returns:
            Filtered list of DatasetModel instances
        """
        filtered = datasets
        
        if country:
            filtered = [d for d in filtered if d.country == country.lower()]
        
        if year:
            filtered = [d for d in filtered if d.year == year]
        
        if source:
            filtered = [d for d in filtered if d.source == source]
        
        return filtered
    
    @staticmethod
    def get_dataset_filename(dataset: DatasetModel) -> str:
        """Generate a standard filename for a dataset.
        
        Args:
            dataset: DatasetModel
            
        Returns:
            Standard filename string
        """
        parts = [dataset.name]
        
        if dataset.year:
            parts.append(str(dataset.year))
        
        if dataset.version:
            parts.append(f"v{dataset.version}")
        
        return "_".join(parts) + ".h5"
    
    @staticmethod
    def merge_dataset_metadata(
        base_dataset: DatasetModel,
        updates: Dict[str, Any]
    ) -> DatasetModel:
        """Merge dataset metadata with updates.
        
        Args:
            base_dataset: Base dataset model
            updates: Dictionary of updates
            
        Returns:
            Updated DatasetModel instance
        """
        dataset_dict = DatasetHandler.dataset_to_dict(base_dataset)
        dataset_dict.update(updates)
        return DatasetHandler.dataset_from_dict(dataset_dict)