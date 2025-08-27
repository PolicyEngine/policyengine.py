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
            config: SimulationOrchestratorConfig with storage settings
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
                # Check if this is a year key with nested data
                if isinstance(key, (int, str)) and str(key).isdigit() and isinstance(value, dict):
                    # This is year-structured data
                    year_group = f.create_group(str(key))
                    self._save_year_data(year_group, value)
                elif isinstance(value, pd.DataFrame):
                    # Save DataFrame as a dictionary of columns
                    group = f.create_group(key)
                    
                    # Store each column as a dataset
                    for col in value.columns:
                        col_str = str(col)  # Ensure column name is a string
                        group.create_dataset(f"col_{col_str}", data=value[col].values)
                    
                    # Store column names and index as datasets (not attributes) to avoid size limits
                    columns_data = np.array([str(c) for c in value.columns], dtype='S')
                    group.create_dataset('_columns', data=columns_data)
                    
                    # Store index as dataset
                    group.create_dataset('_index', data=value.index.values)
                    
                    # Store metadata about the DataFrame
                    group.attrs['is_dataframe'] = True
                    group.attrs['shape'] = value.shape
                    
                elif isinstance(value, (np.ndarray, list)):
                    # Save array
                    f.create_dataset(key, data=np.array(value))
                elif isinstance(value, dict):
                    # For small dicts, save as JSON in attributes
                    # For large dicts, save as a group
                    json_str = json.dumps(value)
                    if len(json_str) < 64000:  # HDF5 attribute size limit is ~64KB
                        f.attrs[key] = json_str
                    else:
                        # Save large dict as a dataset
                        f.create_dataset(key, data=np.array(json_str, dtype='S'))
                else:
                    # Save scalar
                    f.attrs[key] = value
        
        # Return file size in MB
        return os.path.getsize(filepath) / (1024 * 1024)
    
    def _save_year_data(self, group: h5py.Group, data: Dict[str, Any]):
        """Save year-level data to HDF5 group."""
        for key, value in data.items():
            if isinstance(value, pd.DataFrame):
                # Save DataFrame
                df_group = group.create_group(key)
                
                # Store each column as a dataset
                for col in value.columns:
                    col_str = str(col)
                    df_group.create_dataset(f"col_{col_str}", data=value[col].values)
                
                # Store column names and index as datasets
                columns_data = np.array([str(c) for c in value.columns], dtype='S')
                df_group.create_dataset('_columns', data=columns_data)
                df_group.create_dataset('_index', data=value.index.values)
                
                # Store metadata
                df_group.attrs['is_dataframe'] = True
                df_group.attrs['shape'] = value.shape
            
            elif isinstance(value, dict):
                # Nested dict - create subgroup
                subgroup = group.create_group(key)
                self._save_year_data(subgroup, value)
            
            elif isinstance(value, (np.ndarray, list)):
                # Save array
                group.create_dataset(key, data=np.array(value))
            
            else:
                # Save scalar as attribute
                group.attrs[key] = value
    
    def _load_from_h5(self, filepath: str) -> Dict[str, Any]:
        """Load data from HDF5 file."""
        data = {}
        with h5py.File(filepath, 'r') as f:
            # Load attributes (scalars and small JSON)
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
                    # Check if this is a year group (numeric key)
                    if key.isdigit():
                        # Load year data
                        data[int(key)] = self._load_year_data(item)
                    # Check if it's a DataFrame
                    elif item.attrs.get('is_dataframe', False):
                        # Reconstruct DataFrame
                        # Load column names
                        if '_columns' in item:
                            columns = [col.decode('utf-8') if isinstance(col, bytes) else col 
                                     for col in item['_columns'][:]]
                        else:
                            columns = []
                        
                        # Load data for each column
                        df_data = {}
                        for col in columns:
                            col_key = f"col_{col}"
                            if col_key in item:
                                df_data[col] = item[col_key][:]
                        
                        # Create DataFrame
                        if df_data:
                            df = pd.DataFrame(df_data)
                            
                            # Restore index if available
                            if '_index' in item:
                                df.index = item['_index'][:]
                            
                            data[key] = df
                    else:
                        # Handle other group types (shouldn't happen with current save logic)
                        group_data = {}
                        for subkey in item.keys():
                            if not subkey.startswith('_'):
                                group_data[subkey] = np.array(item[subkey])
                        data[key] = group_data
                else:
                    # Load dataset
                    arr = np.array(item)
                    # Check if it's a JSON string stored as dataset (for large dicts)
                    if arr.dtype.kind in ['S', 'U'] and len(arr.shape) == 0:
                        # It's a scalar string, might be JSON
                        try:
                            str_val = arr.item()
                            if isinstance(str_val, bytes):
                                str_val = str_val.decode('utf-8')
                            if str_val.startswith('{') or str_val.startswith('['):
                                data[key] = json.loads(str_val)
                            else:
                                data[key] = str_val
                        except:
                            data[key] = arr
                    else:
                        data[key] = arr
        
        return data
    
    def _load_year_data(self, group: h5py.Group) -> Dict[str, Any]:
        """Load year-level data from HDF5 group."""
        data = {}
        
        # Load attributes
        for key, value in group.attrs.items():
            data[key] = value
        
        # Load subgroups and datasets
        for key in group.keys():
            item = group[key]
            if isinstance(item, h5py.Group):
                if item.attrs.get('is_dataframe', False):
                    # Reconstruct DataFrame
                    if '_columns' in item:
                        columns = [col.decode('utf-8') if isinstance(col, bytes) else col 
                                 for col in item['_columns'][:]]
                    else:
                        columns = []
                    
                    # Load data for each column
                    df_data = {}
                    for col in columns:
                        col_key = f"col_{col}"
                        if col_key in item:
                            df_data[col] = item[col_key][:]
                    
                    # Create DataFrame
                    if df_data:
                        df = pd.DataFrame(df_data)
                        
                        # Restore index if available
                        if '_index' in item:
                            df.index = item['_index'][:]
                        
                        data[key] = df
                else:
                    # Recursively load nested group
                    data[key] = self._load_year_data(item)
            else:
                # Load dataset
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