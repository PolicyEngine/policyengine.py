"""Storage backend for HDF5 and cloud storage operations."""

import os
import json
import h5py
import numpy as np
from typing import Dict, Any, Optional
import pandas as pd


class StorageBackend:
    """Handles file storage operations for simulations."""
    
    def __init__(self, config):
        """Initialize storage backend.
        
        Args:
            config: DatabaseConfig with storage settings
        """
        self.config = config
    
    def save_simulation(
        self,
        sim_id: str,
        country: str,
        scenario: str,
        dataset: str,
        year: int,
        data: Dict[str, Any]
    ) -> tuple[str, float]:
        """Save simulation data to storage.
        
        All simulations stored with {uuid}.h5 pattern in single folder.
        
        Returns:
            Tuple of (filepath/url, file_size_mb)
        """
        filename = f"{sim_id}.h5"
        
        if self.config.storage_mode == "local":
            filepath = os.path.join(
                self.config.local_storage_path,
                filename
            )
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            file_size_mb = self._save_to_h5(filepath, data)
            return filepath, file_size_mb
            
        elif self.config.storage_mode == "cloud":
            if not self.config.gcs_bucket:
                raise ValueError("GCS bucket not configured for cloud storage")
            
            # Save to temporary file first
            temp_path = os.path.join(self.config.local_storage_path, "temp", filename)
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            file_size_mb = self._save_to_h5(temp_path, data)
            
            # Upload to GCS
            gcs_path = f"simulations/{filename}"
            self._upload_to_gcs(temp_path, self.config.gcs_bucket, gcs_path)
            
            # Clean up temp file
            os.remove(temp_path)
            return f"gs://{self.config.gcs_bucket}/{gcs_path}", file_size_mb
        else:
            raise ValueError(f"Unknown storage mode: {self.config.storage_mode}")
    
    def load_simulation(
        self,
        sim_id: str,
        country: str,
        scenario: str,
        dataset: str,
        year: int
    ) -> Optional[Dict[str, Any]]:
        """Load simulation data from storage.
        
        All simulations stored with {uuid}.h5 pattern in single folder.
        
        Returns:
            Dictionary with simulation data or None if not found
        """
        filename = f"{sim_id}.h5"
        
        if self.config.storage_mode == "local":
            filepath = os.path.join(
                self.config.local_storage_path,
                filename
            )
            
            if not os.path.exists(filepath):
                return None
            
            return self._load_from_h5(filepath)
            
        elif self.config.storage_mode == "cloud":
            gcs_path = f"simulations/{filename}"
            
            # Download to temp file
            temp_path = os.path.join(self.config.local_storage_path, "temp", filename)
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            
            try:
                self._download_from_gcs(self.config.gcs_bucket, gcs_path, temp_path)
                data = self._load_from_h5(temp_path)
                os.remove(temp_path)
                return data
            except Exception:
                return None
        else:
            raise ValueError(f"Unknown storage mode: {self.config.storage_mode}")
    
    def _save_to_h5(self, filepath: str, data: Dict[str, Any]) -> float:
        """Save data to HDF5 file.
        
        Returns:
            File size in MB
        """
        with h5py.File(filepath, 'w') as f:
            for key, value in data.items():
                if isinstance(value, pd.DataFrame):
                    # Save DataFrame
                    group = f.create_group(key)
                    for col in value.columns:
                        group.create_dataset(col, data=value[col].values)
                    # Store column names and index
                    group.attrs['columns'] = list(value.columns)
                    group.attrs['index'] = list(value.index)
                elif isinstance(value, (np.ndarray, list)):
                    # Save array
                    f.create_dataset(key, data=np.array(value))
                elif isinstance(value, dict):
                    # Save dict as JSON in attributes
                    f.attrs[key] = json.dumps(value)
                else:
                    # Save scalar
                    f.attrs[key] = value
        
        # Return file size in MB
        return os.path.getsize(filepath) / (1024 * 1024)
    
    def _load_from_h5(self, filepath: str) -> Dict[str, Any]:
        """Load data from HDF5 file."""
        data = {}
        with h5py.File(filepath, 'r') as f:
            # Load attributes (scalars and JSON)
            for key, value in f.attrs.items():
                if isinstance(value, str) and value.startswith('{'):
                    # Try to parse as JSON
                    try:
                        data[key] = json.loads(value)
                    except:
                        data[key] = value
                else:
                    data[key] = value
            
            # Load groups and datasets
            for key in f.keys():
                item = f[key]
                if isinstance(item, h5py.Group):
                    # Reconstruct DataFrame
                    df_data = {}
                    for col in item.keys():
                        df_data[col] = item[col][:]
                    
                    if 'columns' in item.attrs and 'index' in item.attrs:
                        df = pd.DataFrame(df_data, columns=item.attrs['columns'])
                        df.index = item.attrs['index']
                    else:
                        df = pd.DataFrame(df_data)
                    
                    data[key] = df
                else:
                    # Load array
                    data[key] = np.array(item)
        
        return data
    
    def _upload_to_gcs(self, local_path: str, bucket_name: str, gcs_path: str):
        """Upload file to Google Cloud Storage."""
        try:
            from google.cloud import storage
            client = storage.Client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(gcs_path)
            blob.upload_from_filename(local_path)
        except ImportError:
            raise ImportError("google-cloud-storage required for cloud storage mode")
    
    def _download_from_gcs(self, bucket_name: str, gcs_path: str, local_path: str):
        """Download file from Google Cloud Storage."""
        try:
            from google.cloud import storage
            client = storage.Client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(gcs_path)
            blob.download_to_filename(local_path)
        except ImportError:
            raise ImportError("google-cloud-storage required for cloud storage mode")