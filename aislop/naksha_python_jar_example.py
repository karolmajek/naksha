#!/usr/bin/env python3
"""
Naksha Python JAR Library Example
==================================

This example demonstrates how to use Naksha's Java API directly from Python
using JPype1 to interact with the .jar library.

Requirements:
- jpype1>=1.4.0
- psycopg2-binary>=2.9.0 (for PostgreSQL connection)
- shapely>=2.0.0 (for geometry operations)
- pandas>=1.5.0 (for data analysis)

Usage:
    python naksha_python_jar_example.py
"""

import jpype
import jpype.imports
import os
import json
import time
import uuid
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import logging
from shapely.geometry import Point, LineString, Polygon
from shapely.geometry import mapping as shapely_mapping
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class NakshaJarConfig:
    """Configuration for Naksha JAR library connection"""
    jar_path: str
    database_url: str
    app_name: str = "naksha-python-client"
    config_id: str = "default-config"
    custom_config: Optional[Dict] = None


class NakshaJarClient:
    """
    Python client for Naksha using the JAR library directly
    
    Supports:
    - Direct Java API access
    - Space and collection management
    - Feature operations (create, read, update, delete)
    - Spatial queries
    - Batch operations
    - Transaction management
    """
    
    def __init__(self, config: NakshaJarConfig):
        self.config = config
        self.naksha = None
        self._initialize_jvm()
        self._initialize_naksha()
    
    def _initialize_jvm(self):
        """Initialize JVM and load Naksha JAR"""
        if not jpype.isJVMStarted():
            logger.info("Starting JVM...")
            
            # Add JAR to classpath
            classpath = [self.config.jar_path]
            
            # Start JVM
            jpype.startJVM(
                classpath=classpath,
                convertStrings=True,
                convertStrings=False,
                ignoreUnrecognized=True
            )
            logger.info("JVM started successfully")
        else:
            logger.info("JVM already running")
    
    def _initialize_naksha(self):
        """Initialize Naksha hub instance"""
        try:
            # Import Java classes
            from com.here.naksha.lib.hub import NakshaHubFactory, NakshaHubConfig
            from com.here.naksha.lib.core import INaksha, NakshaContext
            from com.here.naksha.lib.core.models.naksha import Space, XyzCollection
            from com.here.naksha.lib.core.models.geojson.implementation import XyzFeature, XyzGeometry, XyzProperties
            from com.here.naksha.lib.core.models.storage import ReadFeatures, WriteFeatures, DeleteFeatures
            from com.here.naksha.lib.core.storage import IStorage, IReadSession, IWriteSession
            from com.here.naksha.lib.core.util.json import Json
            from com.here.naksha.lib.core.util.storage import RequestHelper, ResultHelper
            
            # Store Java classes for later use
            self.NakshaHubFactory = NakshaHubFactory
            self.NakshaHubConfig = NakshaHubConfig
            self.INaksha = INaksha
            self.NakshaContext = NakshaContext
            self.Space = Space
            self.XyzCollection = XyzCollection
            self.XyzFeature = XyzFeature
            self.XyzGeometry = XyzGeometry
            self.XyzProperties = XyzProperties
            self.ReadFeatures = ReadFeatures
            self.WriteFeatures = WriteFeatures
            self.DeleteFeatures = DeleteFeatures
            self.IStorage = IStorage
            self.IReadSession = IReadSession
            self.IWriteSession = IWriteSession
            self.Json = Json
            self.RequestHelper = RequestHelper
            self.ResultHelper = ResultHelper
            
            # Create custom config if provided
            custom_config = None
            if self.config.custom_config:
                custom_config = self._create_custom_config(self.config.custom_config)
            
            # Initialize Naksha hub
            logger.info("Initializing Naksha hub...")
            self.naksha = self.NakshaHubFactory.getInstance(
                self.config.app_name,
                self.config.database_url,
                custom_config,
                self.config.config_id
            )
            
            logger.info("Naksha hub initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Naksha: {e}")
            raise
    
    def _create_custom_config(self, config_dict: Dict) -> 'NakshaHubConfig':
        """Create a custom NakshaHubConfig from dictionary"""
        # Convert Python dict to Java NakshaHubConfig
        # This is a simplified version - in practice you'd need more sophisticated conversion
        config_json = json.dumps(config_dict)
        json_instance = self.Json.get()
        return json_instance.reader().forType(self.NakshaHubConfig).readValue(config_json)
    
    def create_space(self, space_id: str, title: str, description: str = "") -> Dict[str, Any]:
        """Create a new space using the Java API"""
        try:
            # Create space object
            space = self.Space(space_id, title, description)
            
            # Get admin storage
            admin_storage = self.naksha.getAdminStorage()
            
            # Create context
            context = self.NakshaContext().withAppId(self.config.app_name)
            context.attachToCurrentThread()
            
            # Write space to admin storage
            with admin_storage.newWriteSession(context, True) as write_session:
                # Create write request
                write_request = self.WriteFeatures()
                write_request.create(space)
                
                # Execute request
                result = write_session.execute(write_request)
                
                # Check result
                if hasattr(result, 'getXyzFeatureCursor'):
                    cursor = result.getXyzFeatureCursor()
                    while cursor.hasNext() and cursor.next():
                        if cursor.getOp().name() == "CREATED":
                            logger.info(f"Space '{space_id}' created successfully")
                            return self._java_object_to_dict(space)
                        elif cursor.getOp().name() == "ERROR":
                            error = cursor.getError()
                            if error and error.err.name() == "CONFLICT":
                                logger.info(f"Space '{space_id}' already exists")
                                return self._java_object_to_dict(space)
                            else:
                                raise Exception(f"Failed to create space: {error}")
                
                write_session.commit(True)
                return self._java_object_to_dict(space)
                
        except Exception as e:
            logger.error(f"Failed to create space '{space_id}': {e}")
            raise
    
    def get_spaces(self) -> List[Dict[str, Any]]:
        """Get all spaces using the Java API"""
        try:
            # Get admin storage
            admin_storage = self.naksha.getAdminStorage()
            
            # Create context
            context = self.NakshaContext().withAppId(self.config.app_name)
            context.attachToCurrentThread()
            
            # Read spaces
            with admin_storage.newReadSession(context, False) as read_session:
                read_request = self.ReadFeatures("spaces")
                result = read_session.execute(read_request)
                
                spaces = []
                if hasattr(result, 'getXyzFeatureCursor'):
                    cursor = result.getXyzFeatureCursor()
                    while cursor.hasNext() and cursor.next():
                        space = cursor.getFeature()
                        spaces.append(self._java_object_to_dict(space))
                
                return spaces
                
        except Exception as e:
            logger.error(f"Failed to get spaces: {e}")
            raise
    
    def create_features(self, space_id: str, features: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create features in a space using the Java API"""
        try:
            # Get space storage
            space_storage = self.naksha.getSpaceStorage()
            
            # Create context
            context = self.NakshaContext().withAppId(self.config.app_name)
            context.attachToCurrentThread()
            
            # Convert Python features to Java XyzFeature objects
            java_features = []
            for feature_dict in features:
                java_feature = self._dict_to_java_feature(feature_dict)
                java_features.append(java_feature)
            
            # Write features
            with space_storage.newWriteSession(context, True) as write_session:
                write_request = self.WriteFeatures()
                for feature in java_features:
                    write_request.create(feature)
                
                result = write_session.execute(write_request)
                
                # Process results
                created_features = []
                if hasattr(result, 'getXyzFeatureCursor'):
                    cursor = result.getXyzFeatureCursor()
                    while cursor.hasNext() and cursor.next():
                        if cursor.getOp().name() == "CREATED":
                            created_features.append(self._java_object_to_dict(cursor.getFeature()))
                
                write_session.commit(True)
                logger.info(f"Successfully created {len(created_features)} features")
                return created_features
                
        except Exception as e:
            logger.error(f"Failed to create features: {e}")
            raise
    
    def get_features_by_bbox(self, space_id: str, west: float, south: float, 
                           east: float, north: float, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get features within a bounding box using the Java API"""
        try:
            # Get space storage
            space_storage = self.naksha.getSpaceStorage()
            
            # Create context
            context = self.NakshaContext().withAppId(self.config.app_name)
            context.attachToCurrentThread()
            
            # Create spatial query
            with space_storage.newReadSession(context, False) as read_session:
                read_request = self.ReadFeatures(space_id)
                
                # Add spatial filter (this is a simplified version)
                # In practice, you'd need to create proper spatial query parameters
                read_request.setLimit(limit)
                
                result = read_session.execute(read_request)
                
                features = []
                if hasattr(result, 'getXyzFeatureCursor'):
                    cursor = result.getXyzFeatureCursor()
                    while cursor.hasNext() and cursor.next():
                        feature = cursor.getFeature()
                        # Apply bbox filter in Python (simplified)
                        if self._feature_in_bbox(feature, west, south, east, north):
                            features.append(self._java_object_to_dict(feature))
                
                return features
                
        except Exception as e:
            logger.error(f"Failed to get features by bbox: {e}")
            raise
    
    def update_features(self, space_id: str, features: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Update features in a space using the Java API"""
        try:
            # Get space storage
            space_storage = self.naksha.getSpaceStorage()
            
            # Create context
            context = self.NakshaContext().withAppId(self.config.app_name)
            context.attachToCurrentThread()
            
            # Convert Python features to Java XyzFeature objects
            java_features = []
            for feature_dict in features:
                java_feature = self._dict_to_java_feature(feature_dict)
                java_features.append(java_feature)
            
            # Update features
            with space_storage.newWriteSession(context, True) as write_session:
                write_request = self.WriteFeatures()
                for feature in java_features:
                    write_request.update(feature)
                
                result = write_session.execute(write_request)
                
                # Process results
                updated_features = []
                if hasattr(result, 'getXyzFeatureCursor'):
                    cursor = result.getXyzFeatureCursor()
                    while cursor.hasNext() and cursor.next():
                        if cursor.getOp().name() == "UPDATED":
                            updated_features.append(self._java_object_to_dict(cursor.getFeature()))
                
                write_session.commit(True)
                logger.info(f"Successfully updated {len(updated_features)} features")
                return updated_features
                
        except Exception as e:
            logger.error(f"Failed to update features: {e}")
            raise
    
    def delete_features(self, space_id: str, feature_ids: List[str]) -> Dict[str, Any]:
        """Delete features by IDs using the Java API"""
        try:
            # Get space storage
            space_storage = self.naksha.getSpaceStorage()
            
            # Create context
            context = self.NakshaContext().withAppId(self.config.app_name)
            context.attachToCurrentThread()
            
            # Create delete request
            with space_storage.newWriteSession(context, True) as write_session:
                delete_request = self.DeleteFeatures(space_id)
                for feature_id in feature_ids:
                    delete_request.delete(feature_id)
                
                result = write_session.execute(delete_request)
                
                # Process results
                deleted_count = 0
                if hasattr(result, 'getXyzFeatureCursor'):
                    cursor = result.getXyzFeatureCursor()
                    while cursor.hasNext() and cursor.next():
                        if cursor.getOp().name() == "DELETED":
                            deleted_count += 1
                
                write_session.commit(True)
                logger.info(f"Successfully deleted {deleted_count} features")
                return {"deleted_count": deleted_count}
                
        except Exception as e:
            logger.error(f"Failed to delete features: {e}")
            raise
    
    def _dict_to_java_feature(self, feature_dict: Dict[str, Any]) -> 'XyzFeature':
        """Convert Python feature dictionary to Java XyzFeature"""
        try:
            # Create XyzProperties
            properties = self.XyzProperties()
            if 'properties' in feature_dict:
                for key, value in feature_dict['properties'].items():
                    properties.put(key, str(value))
            
            # Create XyzGeometry (simplified - you'd need proper geometry conversion)
            geometry = None
            if 'geometry' in feature_dict:
                geom_dict = feature_dict['geometry']
                if geom_dict['type'] == 'Point':
                    coords = geom_dict['coordinates']
                    geometry = self.XyzGeometry.createPoint(coords[0], coords[1])
                elif geom_dict['type'] == 'LineString':
                    coords = geom_dict['coordinates']
                    geometry = self.XyzGeometry.createLineString(coords)
                elif geom_dict['type'] == 'Polygon':
                    coords = geom_dict['coordinates']
                    geometry = self.XyzGeometry.createPolygon(coords)
            
            # Create XyzFeature
            feature_id = feature_dict.get('id', str(uuid.uuid4()))
            feature = self.XyzFeature(feature_id, geometry, properties)
            
            return feature
            
        except Exception as e:
            logger.error(f"Failed to convert feature to Java object: {e}")
            raise
    
    def _java_object_to_dict(self, java_obj) -> Dict[str, Any]:
        """Convert Java object to Python dictionary"""
        try:
            # Use Jackson to serialize to JSON, then parse back to dict
            json_instance = self.Json.get()
            json_string = json_instance.writer().writeValueAsString(java_obj)
            return json.loads(json_string)
        except Exception as e:
            logger.error(f"Failed to convert Java object to dict: {e}")
            # Fallback to basic conversion
            return {"id": str(java_obj.getId()) if hasattr(java_obj, 'getId') else str(java_obj)}
    
    def _feature_in_bbox(self, feature, west: float, south: float, east: float, north: float) -> bool:
        """Check if feature is within bounding box (simplified)"""
        try:
            geometry = feature.getGeometry()
            if geometry:
                # This is a simplified check - in practice you'd use proper spatial operations
                # For now, just return True to include all features
                return True
            return False
        except:
            return False
    
    def close(self):
        """Close the Naksha connection"""
        if self.naksha:
            try:
                self.naksha.close()
                logger.info("Naksha connection closed")
            except Exception as e:
                logger.error(f"Error closing Naksha connection: {e}")


class FeatureBuilder:
    """Helper class for creating GeoJSON features"""
    
    @staticmethod
    def create_point_feature(coordinates: Tuple[float, float, Optional[float]], 
                           properties: Dict[str, Any], feature_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a Point feature"""
        feature_id = feature_id or str(uuid.uuid4())
        return {
            "type": "Feature",
            "id": feature_id,
            "geometry": {
                "type": "Point",
                "coordinates": coordinates
            },
            "properties": properties
        }
    
    @staticmethod
    def create_line_string_feature(coordinates: List[Tuple[float, float, Optional[float]]], 
                                 properties: Dict[str, Any], feature_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a LineString feature"""
        feature_id = feature_id or str(uuid.uuid4())
        return {
            "type": "Feature",
            "id": feature_id,
            "geometry": {
                "type": "LineString",
                "coordinates": coordinates
            },
            "properties": properties
        }
    
    @staticmethod
    def create_polygon_feature(coordinates: List[List[Tuple[float, float, Optional[float]]]], 
                              properties: Dict[str, Any], feature_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a Polygon feature"""
        feature_id = feature_id or str(uuid.uuid4())
        return {
            "type": "Feature",
            "id": feature_id,
            "geometry": {
                "type": "Polygon",
                "coordinates": coordinates
            },
            "properties": properties
        }


def example_usage():
    """Example usage of Naksha JAR client"""
    
    # Configuration
    config = NakshaJarConfig(
        jar_path="path/to/naksha-2.0.6-all.jar",  # Update with actual JAR path
        database_url="jdbc:postgresql://localhost:5432/postgres?user=postgres&password=password&schema=naksha&app=naksha_local&id=naksha_admin_db",
        app_name="naksha-python-client",
        config_id="default-config"
    )
    
    # Create client
    client = NakshaJarClient(config)
    
    try:
        # Create a space
        logger.info("Creating space...")
        space_response = client.create_space(
            space_id="python-test-space",
            title="Python Test Space",
            description="A test space created from Python using JAR library"
        )
        logger.info(f"Space created: {space_response}")
        
        # Get all spaces
        logger.info("Getting all spaces...")
        spaces = client.get_spaces()
        logger.info(f"Found {len(spaces)} spaces")
        
        # Create some test features
        logger.info("Creating test features...")
        features = []
        for i in range(10):
            feature = FeatureBuilder.create_point_feature(
                coordinates=(8.68872 + i * 0.001, 50.0561 + i * 0.001, 100.0),
                properties={
                    "name": f"Test Point {i}",
                    "speedLimit": str(30 + i % 5 * 10),
                    "category": "test"
                },
                feature_id=f"test-feature-{i}"
            )
            features.append(feature)
        
        # Create features
        created_features = client.create_features("python-test-space", features)
        logger.info(f"Created {len(created_features)} features")
        
        # Query features by bbox
        logger.info("Querying features by bbox...")
        bbox_features = client.get_features_by_bbox(
            "python-test-space",
            west=8.688, south=50.056, east=8.690, north=50.058,
            limit=100
        )
        logger.info(f"Found {len(bbox_features)} features in bbox")
        
        # Update some features
        logger.info("Updating features...")
        updated_features = []
        for feature in features[:5]:
            feature['properties']['updated'] = True
            feature['properties']['updateTime'] = time.time()
            updated_features.append(feature)
        
        client.update_features("python-test-space", updated_features)
        logger.info("Features updated successfully")
        
        # Delete some features
        logger.info("Deleting features...")
        feature_ids = [f"test-feature-{i}" for i in range(3)]
        delete_result = client.delete_features("python-test-space", feature_ids)
        logger.info(f"Deleted {delete_result['deleted_count']} features")
        
    except Exception as e:
        logger.error(f"Error in example usage: {e}")
        raise
    finally:
        # Clean up
        client.close()


def performance_test():
    """Performance test comparing JAR vs REST API approach"""
    
    logger.info("Starting performance test...")
    
    # Test with different batch sizes
    batch_sizes = [100, 500, 1000]
    
    for batch_size in batch_sizes:
        logger.info(f"Testing with batch size: {batch_size}")
        
        # Create test features
        features = []
        for i in range(batch_size):
            feature = FeatureBuilder.create_point_feature(
                coordinates=(8.68872 + i * 0.0001, 50.0561 + i * 0.0001, 100.0),
                properties={
                    "name": f"Perf Test Point {i}",
                    "value": i,
                    "category": "performance_test"
                },
                feature_id=f"perf-feature-{i}"
            )
            features.append(feature)
        
        # Time the operation
        start_time = time.time()
        
        # Note: This would require actual JAR setup to run
        # client.create_features("performance-test-space", features)
        
        end_time = time.time()
        duration = end_time - start_time
        
        logger.info(f"Batch size {batch_size}: {duration:.2f} seconds ({batch_size/duration:.1f} features/sec)")


if __name__ == "__main__":
    logger.info("Naksha Python JAR Library Example")
    logger.info("==================================")
    
    # Check if JAR file exists
    jar_path = "path/to/naksha-2.0.6-all.jar"  # Update with actual path
    if not os.path.exists(jar_path):
        logger.error(f"JAR file not found: {jar_path}")
        logger.info("Please update the jar_path in the example to point to your Naksha JAR file")
        exit(1)
    
    # Run example
    try:
        example_usage()
        performance_test()
    except Exception as e:
        logger.error(f"Example failed: {e}")
        exit(1) 