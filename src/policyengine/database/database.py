"""Main database class for PolicyEngine."""

from typing import Optional, Dict, Any, List
from sqlalchemy import create_engine, Table, MetaData, Column, String, Integer, Float, Boolean, Text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from pydantic import BaseModel, Field
import warnings

from .models import Base, EntityTypeDataModel, VariableDataModel
from .schema_helpers import get_country_schema_from_package


class DatabaseConfig(BaseModel):
    """Configuration for database connection."""
    
    connection_string: Optional[str] = Field(
        None, 
        description="Database connection string (defaults to SQLite)"
    )
    echo: bool = Field(False, description="Echo SQL statements")
    pool_size: int = Field(5, description="Connection pool size")
    max_overflow: int = Field(10, description="Maximum overflow connections")


class SchemaDefinition(BaseModel):
    """Schema definition for a country's entities and variables."""
    
    country: str
    entities: Dict[str, List[Dict[str, Any]]]  # entity_name -> list of variable definitions


class Database:
    """Main database interface for PolicyEngine data.
    
    This class provides a simple interface to instantiate and use with either
    local or cloud databases. It sets up the connection and creates tables,
    but does not provide helper methods - those should be implemented elsewhere.
    """
    
    def __init__(self, config: Optional[DatabaseConfig] = None, validate_schema: bool = True, countries: Optional[List[str]] = ["uk"]):
        """Initialize database with configuration.
        
        Args:
            config: Database configuration
            validate_schema: If True, validate country schemas on initialization
            countries: List of country codes to initialize (e.g., ['uk', 'us']). 
                      If None, will try to detect available country packages.
        """
        self.config = config or DatabaseConfig()
        self.engine = self._create_engine()
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Use Base.metadata directly instead of creating a new one
        self.metadata = Base.metadata
        self._country_tables: Dict[str, Table] = {}
        
        # Create all tables defined in models
        self.metadata.create_all(bind=self.engine)
        
        # Initialize country tables
        self._initialize_countries(countries)
        
        # Validate schemas if requested
        if validate_schema:
            self._validate_schemas()
    
    def _create_engine(self):
        """Create SQLAlchemy engine."""
        if self.config.connection_string:
            # Cloud database connection
            return create_engine(
                self.config.connection_string,
                echo=self.config.echo,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow
            )
        else:
            # Local SQLite database
            return create_engine(
                "sqlite:///policyengine.db",
                echo=self.config.echo,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool
            )
    
    def get_session(self) -> Session:
        """Get a database session."""
        return self.SessionLocal()
    
    def _initialize_countries(self, countries: Optional[List[str]] = None):
        """Initialize country tables from their packages.
        
        Args:
            countries: List of country codes. If None, detect available packages.
        """
        if countries is None:
            # Try to detect available country packages
            countries = self._detect_available_countries()
        
        for country in countries:
            try:
                self._initialize_country(country)
            except Exception as e:
                warnings.warn(
                    f"Failed to initialize country '{country}': {e}",
                    UserWarning
                )
    
    def _detect_available_countries(self) -> List[str]:
        """Detect which country packages are available."""
        available = []
        
        # Try common country codes
        for country in ['uk', 'us']:
            try:
                # Try to import the package
                if country == 'uk':
                    import policyengine_uk
                    available.append('uk')
                elif country == 'us':
                    import policyengine_us
                    available.append('us')
            except ImportError:
                pass
        
        return available
    
    def _initialize_country(self, country: str):
        """Initialize tables for a specific country.
        
        Args:
            country: Country code (e.g., 'uk', 'us')
        """
        # Check if already initialized by looking at entity_types table
        with self.get_session() as session:
            existing = session.query(EntityTypeDataModel).filter_by(country=country).first()
            if existing:
                # Country already initialized, just load the tables
                self._load_country_tables(country)
                return
        
        # Get schema from package
        try:
            schema = get_country_schema_from_package(country)
        except (ImportError, ValueError) as e:
            raise RuntimeError(f"Cannot initialize country '{country}': {e}")
        
        # Create tables and populate schema tracking
        with self.get_session() as session:
            for entity_name, variables in schema.items():
                table_name = f"{country}_{entity_name}"
                
                # Create entity type record
                entity_type = EntityTypeDataModel(
                    country=country,
                    name=entity_name,
                    table_name=table_name
                )
                session.add(entity_type)
                session.flush()
                
                # Create variable records
                for var_def in variables:
                    variable = VariableDataModel(
                        entity_type_id=entity_type.id,
                        name=var_def['name'],
                        data_type=var_def['data_type'],
                        is_nullable=var_def.get('is_nullable', True),
                        default_value=var_def.get('default_value')
                    )
                    session.add(variable)
                
                # Create actual table
                columns = self._create_columns_from_variables(variables)
                self.create_country_table(table_name, columns)
            
            session.commit()
    
    def _load_country_tables(self, country: str):
        """Load existing country tables into memory.
        
        Args:
            country: Country code
        """
        with self.get_session() as session:
            entity_types = session.query(EntityTypeDataModel).filter_by(country=country).all()
            
            for entity_type in entity_types:
                table_name = entity_type.table_name
                # Just ensure the table is in our cache
                # The table should already exist in the database
                if table_name not in self._country_tables and table_name not in self.metadata.tables:
                    # Reflect the table from the database
                    Table(table_name, self.metadata, autoload_with=self.engine)
    
    def get_country_schema(self, country: str) -> SchemaDefinition:
        """Get the current schema from a country package.
        
        Args:
            country: Country code (e.g., 'uk', 'us')
            
        Returns:
            SchemaDefinition with entity and variable information
        """
        try:
            entities = get_country_schema_from_package(country)
            return SchemaDefinition(country=country, entities=entities)
        except (ImportError, ValueError) as e:
            raise RuntimeError(
                f"Failed to get schema for country '{country}': {e}"
            )
    
    def _get_stored_schema(self, country: str) -> Dict[str, List[Dict[str, Any]]]:
        """Get the stored schema from the database.
        
        Args:
            country: Country code
            
        Returns:
            Dictionary mapping entity names to their variable definitions
        """
        with self.get_session() as session:
            entity_types = session.query(EntityTypeDataModel).filter_by(country=country).all()
            
            schema = {}
            for entity_type in entity_types:
                variables = []
                for var in entity_type.variables:
                    variables.append({
                        'name': var.name,
                        'data_type': var.data_type,
                        'is_nullable': var.is_nullable,
                        'default_value': var.default_value
                    })
                schema[entity_type.name] = variables
            
            return schema
    
    def _validate_schemas(self):
        """Validate that database schemas match country package schemas.
        
        Raises:
            RuntimeError: If schemas don't match
        """
        # Get list of countries from entity_types table
        with self.get_session() as session:
            countries = session.query(EntityTypeDataModel.country).distinct().all()
            countries = [c[0] for c in countries]
        
        for country in countries:
            try:
                current_schema = self.get_country_schema(country)
                stored_schema = self._get_stored_schema(country)
                
                # Compare schemas
                if current_schema.entities != stored_schema:
                    raise RuntimeError(
                        f"Schema mismatch for {country}. "
                        f"Database schema differs from country package schema. "
                        f"Run migrate_schema('{country}') to update."
                    )
            except NotImplementedError:
                # Skip validation if country schema extraction not implemented
                pass
    
    def migrate_schema(self, country: str, dry_run: bool = False) -> List[str]:
        """Migrate database schema to match country package schema.
        
        WARNING: This will drop and add columns/tables as needed, potentially losing data.
        
        Args:
            country: Country code to migrate
            dry_run: If True, only return planned changes without executing
            
        Returns:
            List of migration actions performed/planned
        """
        warnings.warn(
            "Schema migration will modify database structure and may result in data loss. "
            "Ensure you have backups before proceeding.",
            UserWarning
        )
        
        try:
            target_schema = self.get_country_schema(country)
        except NotImplementedError:
            return ["Cannot migrate: Country schema extraction not implemented"]
        
        stored_schema = self._get_stored_schema(country)
        actions = []
        
        with self.get_session() as session:
            # Process each entity type
            for entity_name, target_variables in target_schema.entities.items():
                table_name = f"{country}_{entity_name}"
                
                if entity_name not in stored_schema:
                    # New entity type - create table and record
                    actions.append(f"CREATE TABLE {table_name}")
                    
                    if not dry_run:
                        # Create entity type record
                        entity_type = EntityTypeDataModel(
                            country=country,
                            name=entity_name,
                            table_name=table_name
                        )
                        session.add(entity_type)
                        session.flush()
                        
                        # Create variable records
                        for var_def in target_variables:
                            variable = VariableDataModel(
                                entity_type_id=entity_type.id,
                                name=var_def['name'],
                                data_type=var_def['data_type'],
                                is_nullable=var_def.get('is_nullable', True),
                                default_value=var_def.get('default_value')
                            )
                            session.add(variable)
                        
                        # Create actual table
                        columns = self._create_columns_from_variables(target_variables)
                        self.create_country_table(table_name, columns)
                else:
                    # Existing entity - check for column changes
                    stored_variables = stored_schema[entity_name]
                    stored_var_names = {v['name'] for v in stored_variables}
                    target_var_names = {v['name'] for v in target_variables}
                    
                    # Find columns to add
                    columns_to_add = target_var_names - stored_var_names
                    for col_name in columns_to_add:
                        actions.append(f"ADD COLUMN {table_name}.{col_name}")
                        
                        if not dry_run:
                            # Add to variables table
                            var_def = next(v for v in target_variables if v['name'] == col_name)
                            entity_type = session.query(EntityTypeDataModel).filter_by(
                                country=country, name=entity_name
                            ).first()
                            
                            variable = VariableDataModel(
                                entity_type_id=entity_type.id,
                                name=var_def['name'],
                                data_type=var_def['data_type'],
                                is_nullable=var_def.get('is_nullable', True),
                                default_value=var_def.get('default_value')
                            )
                            session.add(variable)
                            
                            # Add column to actual table
                            self._add_column_to_table(table_name, col_name, var_def)
                    
                    # Find columns to remove
                    columns_to_remove = stored_var_names - target_var_names
                    for col_name in columns_to_remove:
                        actions.append(f"DROP COLUMN {table_name}.{col_name}")
                        
                        if not dry_run:
                            # Remove from variables table
                            entity_type = session.query(EntityTypeDataModel).filter_by(
                                country=country, name=entity_name
                            ).first()
                            variable = session.query(VariableDataModel).filter_by(
                                entity_type_id=entity_type.id, name=col_name
                            ).first()
                            if variable:
                                session.delete(variable)
                            
                            # Drop column from actual table
                            self._drop_column_from_table(table_name, col_name)
            
            # Find entity types to remove
            for entity_name in stored_schema:
                if entity_name not in target_schema.entities:
                    table_name = f"{country}_{entity_name}"
                    actions.append(f"DROP TABLE {table_name}")
                    
                    if not dry_run:
                        # Remove entity type and its variables (cascade)
                        entity_type = session.query(EntityTypeDataModel).filter_by(
                            country=country, name=entity_name
                        ).first()
                        if entity_type:
                            session.delete(entity_type)
                        
                        # Drop actual table
                        self._drop_table(table_name)
            
            if not dry_run:
                session.commit()
        
        return actions
    
    def _create_columns_from_variables(self, variables: List[Dict[str, Any]]) -> Dict[str, Column]:
        """Create SQLAlchemy columns from variable definitions."""
        columns = {}
        
        # Always add an ID column as primary key
        columns['id'] = Column(String, primary_key=True)
        
        for var_def in variables:
            col_name = var_def['name']
            data_type = var_def['data_type']
            is_nullable = var_def.get('is_nullable', True)
            default_value = var_def.get('default_value')
            
            # Map data types to SQLAlchemy types
            if data_type == 'string':
                col_type = String
            elif data_type == 'integer':
                col_type = Integer
            elif data_type == 'float':
                col_type = Float
            elif data_type == 'boolean':
                col_type = Boolean
            elif data_type == 'text':
                col_type = Text
            else:
                col_type = String  # Default to string
            
            columns[col_name] = Column(col_type, nullable=is_nullable, default=default_value)
        
        return columns
    
    def _add_column_to_table(self, table_name: str, column_name: str, var_def: Dict[str, Any]):
        """Add a column to an existing table."""
        # This is database-specific and would need different implementations
        # for different database backends
        with self.engine.connect() as conn:
            data_type = var_def['data_type']
            
            # Map to SQL types
            sql_type_map = {
                'string': 'VARCHAR(255)',
                'integer': 'INTEGER',
                'float': 'REAL',
                'boolean': 'BOOLEAN',
                'text': 'TEXT'
            }
            sql_type = sql_type_map.get(data_type, 'VARCHAR(255)')
            
            # Build ALTER TABLE statement
            nullable = 'NULL' if var_def.get('is_nullable', True) else 'NOT NULL'
            default = f"DEFAULT {var_def['default_value']}" if var_def.get('default_value') is not None else ''
            
            sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {sql_type} {nullable} {default}"
            conn.execute(sql)
            conn.commit()
    
    def _drop_column_from_table(self, table_name: str, column_name: str):
        """Drop a column from an existing table."""
        # Note: SQLite doesn't support DROP COLUMN directly
        # For other databases, this would be simpler
        if self.is_local:
            # SQLite requires recreating the table
            warnings.warn(
                f"SQLite does not support DROP COLUMN. "
                f"Column {column_name} in {table_name} will be ignored but not removed.",
                UserWarning
            )
        else:
            # For other databases
            with self.engine.connect() as conn:
                sql = f"ALTER TABLE {table_name} DROP COLUMN {column_name}"
                conn.execute(sql)
                conn.commit()
    
    def _drop_table(self, table_name: str):
        """Drop a table."""
        with self.engine.connect() as conn:
            sql = f"DROP TABLE IF EXISTS {table_name}"
            conn.execute(sql)
            conn.commit()
        
        # Remove from cache
        if table_name in self._country_tables:
            del self._country_tables[table_name]
    
    def create_country_table(self, table_name: str, columns: Dict[str, Column]) -> Table:
        """Create a dynamic table based on country package metadata.
        
        This allows country packages to define tables dynamically at runtime
        without needing predefined models. For example, uk_person, us_household, etc.
        will be created based on the entities and variables defined in the country packages.
        
        Args:
            table_name: Name of the table to create (e.g., 'uk_person', 'us_household')
            columns: Dictionary mapping column names to SQLAlchemy Column objects
            
        Returns:
            The created SQLAlchemy Table object
        """
        # Check if table already exists in memory
        if table_name in self._country_tables:
            return self._country_tables[table_name]
        
        # Check if table already exists in metadata
        if table_name in self.metadata.tables:
            return self.metadata.tables[table_name]
        
        # Create new table with columns
        column_list = []
        for col_name, col_def in columns.items():
            # Ensure column has a name
            if col_def.name is None:
                col_def.name = col_name
            column_list.append(col_def)
        
        table = Table(table_name, self.metadata, *column_list, extend_existing=True)
        
        # Store in cache
        self._country_tables[table_name] = table
        
        # Create the table in the database
        self.metadata.create_all(bind=self.engine, tables=[table])
        
        return table
    
    def get_country_table(self, table_name: str) -> Optional[Table]:
        """Get a registered country-specific table.
        
        Args:
            table_name: Name of the table (e.g., 'uk_person', 'us_household')
            
        Returns:
            The SQLAlchemy Table object if registered, None otherwise
        """
        # Check cache first
        if table_name in self._country_tables:
            return self._country_tables[table_name]
        
        # Check metadata
        if table_name in self.metadata.tables:
            return self.metadata.tables[table_name]
        
        return None
    
    @property
    def is_cloud(self) -> bool:
        """Check if using cloud database."""
        return self.config.connection_string is not None
    
    @property
    def is_local(self) -> bool:
        """Check if using local database."""
        return self.config.connection_string is None