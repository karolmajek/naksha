#!/usr/bin/env python3
"""
Naksha Python Client Example
============================

This example demonstrates how to connect to Naksha using Python with various
data access methods, batch operations, and best practices.

Requirements:
- requests>=2.28.0
- pandas>=1.5.0 (for data analysis)
- shapely>=2.0.0 (for geometry operations)
- concurrent.futures (built-in, for parallel processing)

Usage:
    python naksha_python_example.py
"""

import requests
import json
import time
import uuid
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
from shapely.geometry import Point, LineString, Polygon
from shapely.geometry import mapping as shapely_mapping
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class NakshaConfig:
    """Configuration for Naksha connection"""
    base_url: str
    access_token: str
    timeout: int = 30
    max_retries: int = 3
    batch_size: int = 1000


class NakshaClient:
    """
    Python client for Naksha REST API
    
    Supports:
    - Batch operations (create, update, delete)
    - Spatial queries (bbox, radius, tile)
    - Feature iteration and search
    - Parallel processing
    - Error handling and retries
    """
    
    def __init__(self, config: NakshaConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {config.access_token}',
            'Content-Type': 'application/json',
            'User-Agent': 'NakshaPythonClient/1.0'
        })
        self.session.timeout = config.timeout
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, 
                     params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request with retry logic"""
        url = f"{self.config.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        for attempt in range(self.config.max_retries):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params
                )
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                if attempt == self.config.max_retries - 1:
                    raise Exception(f"Request failed after {self.config.max_retries} attempts: {e}")
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                time.sleep(2 ** attempt)  # Exponential backoff
    
    def create_space(self, space_id: str, title: str, description: str = "") -> Dict[str, Any]:
        """Create a new space"""
        space_data = {
            "id": space_id,
            "title": title,
            "description": description
        }
        return self._make_request("POST", "/hub/spaces", data=space_data)
    
    def get_spaces(self) -> List[Dict[str, Any]]:
        """Get all spaces accessible to the user"""
        response = self._make_request("GET", "/hub/spaces")
        return response.get("features", [])
    
    def delete_space(self, space_id: str) -> Dict[str, Any]:
        """Delete a space"""
        return self._make_request("DELETE", f"/hub/spaces/{space_id}")
    
    def batch_upsert_features(self, space_id: str, features: List[Dict[str, Any]], 
                             batch_size: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Batch upsert features (create or update)
        
        Args:
            space_id: Target space ID
            features: List of GeoJSON features
            batch_size: Optional batch size (defaults to config.batch_size)
        
        Returns:
            List of response data from all batches
        """
        batch_size = batch_size or self.config.batch_size
        all_responses = []
        
        # Split features into batches
        for i in range(0, len(features), batch_size):
            batch = features[i:i + batch_size]
            feature_collection = {
                "type": "FeatureCollection",
                "features": batch
            }
            
            logger.info(f"Processing batch {i//batch_size + 1}/{(len(features) + batch_size - 1)//batch_size}")
            
            try:
                response = self._make_request("PUT", f"/hub/spaces/{space_id}/features", 
                                           data=feature_collection)
                all_responses.append(response)
                logger.info(f"Successfully processed {len(batch)} features")
            except Exception as e:
                logger.error(f"Failed to process batch: {e}")
                raise
        
        return all_responses
    
    def batch_create_features(self, space_id: str, features: List[Dict[str, Any]], 
                            batch_size: Optional[int] = None) -> List[Dict[str, Any]]:
        """Batch create features (POST method - creates or patches)"""
        batch_size = batch_size or self.config.batch_size
        all_responses = []
        
        for i in range(0, len(features), batch_size):
            batch = features[i:i + batch_size]
            feature_collection = {
                "type": "FeatureCollection",
                "features": batch
            }
            
            logger.info(f"Creating batch {i//batch_size + 1}/{(len(features) + batch_size - 1)//batch_size}")
            
            try:
                response = self._make_request("POST", f"/hub/spaces/{space_id}/features", 
                                           data=feature_collection)
                all_responses.append(response)
                logger.info(f"Successfully created {len(batch)} features")
            except Exception as e:
                logger.error(f"Failed to create batch: {e}")
                raise
        
        return all_responses
    
    def get_features_by_ids(self, space_id: str, feature_ids: List[str]) -> List[Dict[str, Any]]:
        """Get features by their IDs"""
        params = {"id": ",".join(feature_ids)}
        response = self._make_request("GET", f"/hub/spaces/{space_id}/features", params=params)
        return response.get("features", [])
    
    def get_features_by_bbox(self, space_id: str, west: float, south: float, 
                            east: float, north: float, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get features within a bounding box"""
        params = {
            "west": west,
            "south": south,
            "east": east,
            "north": north,
            "limit": limit
        }
        response = self._make_request("GET", f"/hub/spaces/{space_id}/bbox", params=params)
        return response.get("features", [])
    
    def get_features_by_radius(self, space_id: str, lat: float, lon: float, 
                              radius: float, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get features within a radius of a point"""
        params = {
            "lat": lat,
            "lon": lon,
            "radius": radius,
            "limit": limit
        }
        response = self._make_request("GET", f"/hub/spaces/{space_id}/spatial", params=params)
        return response.get("features", [])
    
    def search_features(self, space_id: str, tags: Optional[List[str]] = None, 
                       properties_query: Optional[Dict] = None, limit: int = 1000) -> List[Dict[str, Any]]:
        """Search features by tags and/or properties"""
        params = {"limit": limit}
        
        if tags:
            params["tags"] = ",".join(tags)
        
        if properties_query:
            # Convert properties query to string format
            for key, value in properties_query.items():
                params[f"p.{key}"] = str(value)
        
        response = self._make_request("GET", f"/hub/spaces/{space_id}/search", params=params)
        return response.get("features", [])
    
    def iterate_all_features(self, space_id: str, batch_size: int = 1000) -> List[Dict[str, Any]]:
        """Iterate through all features in a space"""
        all_features = []
        handle = None
        
        while True:
            params = {"limit": batch_size}
            if handle:
                params["handle"] = handle
            
            response = self._make_request("GET", f"/hub/spaces/{space_id}/iterate", params=params)
            features = response.get("features", [])
            all_features.extend(features)
            
            # Check if there are more features
            handle = response.get("_handle")
            if not handle:
                break
            
            logger.info(f"Retrieved {len(features)} features, total: {len(all_features)}")
        
        return all_features
    
    def delete_features(self, space_id: str, feature_ids: List[str]) -> Dict[str, Any]:
        """Delete features by their IDs"""
        params = {"id": ",".join(feature_ids)}
        return self._make_request("DELETE", f"/hub/spaces/{space_id}/features", params=params)
    
    def parallel_batch_upsert(self, space_id: str, features: List[Dict[str, Any]], 
                             max_workers: int = 4) -> List[Dict[str, Any]]:
        """Parallel batch upsert for high-performance data loading"""
        batch_size = self.config.batch_size
        batches = [features[i:i + batch_size] for i in range(0, len(features), batch_size)]
        
        all_responses = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all batches
            future_to_batch = {
                executor.submit(self._upsert_batch, space_id, batch): batch 
                for batch in batches
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_batch):
                batch = future_to_batch[future]
                try:
                    response = future.result()
                    all_responses.append(response)
                    logger.info(f"Completed batch of {len(batch)} features")
                except Exception as e:
                    logger.error(f"Batch failed: {e}")
                    raise
        
        return all_responses
    
    def _upsert_batch(self, space_id: str, features: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Helper method for parallel batch upsert"""
        feature_collection = {
            "type": "FeatureCollection",
            "features": features
        }
        return self._make_request("PUT", f"/hub/spaces/{space_id}/features", data=feature_collection)


class FeatureBuilder:
    """Helper class for building GeoJSON features"""
    
    @staticmethod
    def create_point_feature(coordinates: Tuple[float, float, Optional[float]], 
                           properties: Dict[str, Any], feature_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a Point feature"""
        feature = {
            "type": "Feature",
            "properties": properties,
            "geometry": {
                "type": "Point",
                "coordinates": list(coordinates)
            }
        }
        
        if feature_id:
            feature["id"] = feature_id
        
        return feature
    
    @staticmethod
    def create_line_string_feature(coordinates: List[Tuple[float, float, Optional[float]]], 
                                 properties: Dict[str, Any], feature_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a LineString feature"""
        feature = {
            "type": "Feature",
            "properties": properties,
            "geometry": {
                "type": "LineString",
                "coordinates": [list(coord) for coord in coordinates]
            }
        }
        
        if feature_id:
            feature["id"] = feature_id
        
        return feature
    
    @staticmethod
    def create_polygon_feature(coordinates: List[List[Tuple[float, float, Optional[float]]]], 
                              properties: Dict[str, Any], feature_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a Polygon feature"""
        feature = {
            "type": "Feature",
            "properties": properties,
            "geometry": {
                "type": "Polygon",
                "coordinates": [[list(coord) for coord in ring] for ring in coordinates]
            }
        }
        
        if feature_id:
            feature["id"] = feature_id
        
        return feature
    
    @staticmethod
    def add_tags(feature: Dict[str, Any], tags: List[str]) -> Dict[str, Any]:
        """Add tags to a feature"""
        if "@ns:com:here:xyz" not in feature["properties"]:
            feature["properties"]["@ns:com:here:xyz"] = {}
        
        feature["properties"]["@ns:com:here:xyz"]["tags"] = tags
        return feature


def example_usage():
    """Example usage of the Naksha Python client"""
    
    # Configuration
    config = NakshaConfig(
        base_url="https://naksha-v2-dev.ext.mapcreator.here.com",
        access_token="your_access_token_here",
        batch_size=500
    )
    
    # Create client
    client = NakshaClient(config)
    
    # Example 1: Create a space
    try:
        space_response = client.create_space(
            space_id="example-space-123",
            title="Example Space",
            description="A space for testing Naksha Python client"
        )
        logger.info(f"Created space: {space_response}")
    except Exception as e:
        logger.error(f"Failed to create space: {e}")
        return
    
    space_id = "example-space-123"
    
    # Example 2: Create sample features
    features = []
    
    # Create some point features
    for i in range(100):
        feature = FeatureBuilder.create_point_feature(
            coordinates=(8.68872 + i * 0.001, 50.0561 + i * 0.001, 100.0),
            properties={
                "speedLimit": str(30 + (i % 5) * 10),
                "featureType": "traffic_sign",
                "index": i
            },
            feature_id=f"feature-{i}"
        )
        
        # Add tags
        feature = FeatureBuilder.add_tags(feature, [f"tag-{i % 3}", "example"])
        features.append(feature)
    
    # Example 3: Batch upsert features
    try:
        responses = client.batch_upsert_features(space_id, features)
        logger.info(f"Successfully upserted {len(features)} features")
    except Exception as e:
        logger.error(f"Failed to upsert features: {e}")
        return
    
    # Example 4: Query features by bounding box
    try:
        bbox_features = client.get_features_by_bbox(
            space_id, 
            west=8.68, south=50.05, east=8.69, north=50.06
        )
        logger.info(f"Found {len(bbox_features)} features in bbox")
    except Exception as e:
        logger.error(f"Failed to query bbox: {e}")
    
    # Example 5: Search features by tags
    try:
        tagged_features = client.search_features(
            space_id, 
            tags=["tag-0", "example"]
        )
        logger.info(f"Found {len(tagged_features)} features with tags")
    except Exception as e:
        logger.error(f"Failed to search features: {e}")
    
    # Example 6: Parallel batch processing for large datasets
    large_features = []
    for i in range(10000):
        feature = FeatureBuilder.create_point_feature(
            coordinates=(8.68872 + (i % 100) * 0.001, 50.0561 + (i // 100) * 0.001, 100.0),
            properties={
                "speedLimit": str(30 + (i % 5) * 10),
                "featureType": "traffic_sign",
                "index": i
            },
            feature_id=f"large-feature-{i}"
        )
        feature = FeatureBuilder.add_tags(feature, [f"tag-{i % 10}", "large-dataset"])
        large_features.append(feature)
    
    try:
        logger.info("Starting parallel batch processing...")
        start_time = time.time()
        responses = client.parallel_batch_upsert(space_id, large_features, max_workers=4)
        end_time = time.time()
        logger.info(f"Parallel processing completed in {end_time - start_time:.2f} seconds")
    except Exception as e:
        logger.error(f"Failed parallel processing: {e}")
    
    # Example 7: Iterate all features
    try:
        logger.info("Starting feature iteration...")
        all_features = client.iterate_all_features(space_id)
        logger.info(f"Total features in space: {len(all_features)}")
    except Exception as e:
        logger.error(f"Failed to iterate features: {e}")
    
    # Example 8: Clean up - delete space
    try:
        client.delete_space(space_id)
        logger.info(f"Deleted space: {space_id}")
    except Exception as e:
        logger.error(f"Failed to delete space: {e}")


def performance_comparison():
    """Compare different batch sizes for performance"""
    
    config = NakshaConfig(
        base_url="https://naksha-v2-dev.ext.mapcreator.here.com",
        access_token="your_access_token_here"
    )
    
    client = NakshaClient(config)
    space_id = "performance-test-space"
    
    # Create test space
    try:
        client.create_space(space_id, "Performance Test Space")
    except Exception as e:
        logger.error(f"Failed to create test space: {e}")
        return
    
    # Generate test data
    test_features = []
    for i in range(1000):
        feature = FeatureBuilder.create_point_feature(
            coordinates=(8.68872 + i * 0.001, 50.0561 + i * 0.001, 100.0),
            properties={"index": i, "test": True},
            feature_id=f"perf-test-{i}"
        )
        test_features.append(feature)
    
    # Test different batch sizes
    batch_sizes = [100, 500, 1000, 2000]
    results = {}
    
    for batch_size in batch_sizes:
        logger.info(f"Testing batch size: {batch_size}")
        start_time = time.time()
        
        try:
            responses = client.batch_upsert_features(space_id, test_features, batch_size)
            end_time = time.time()
            duration = end_time - start_time
            results[batch_size] = duration
            logger.info(f"Batch size {batch_size}: {duration:.2f} seconds")
        except Exception as e:
            logger.error(f"Failed with batch size {batch_size}: {e}")
            results[batch_size] = None
    
    # Print results
    logger.info("\nPerformance Results:")
    for batch_size, duration in results.items():
        if duration:
            features_per_second = len(test_features) / duration
            logger.info(f"Batch size {batch_size}: {duration:.2f}s ({features_per_second:.0f} features/sec)")
        else:
            logger.info(f"Batch size {batch_size}: FAILED")
    
    # Clean up
    try:
        client.delete_space(space_id)
    except Exception as e:
        logger.error(f"Failed to clean up: {e}")


if __name__ == "__main__":
    logger.info("Starting Naksha Python Client Example")
    
    # Run basic example
    example_usage()
    
    # Run performance comparison
    # performance_comparison()
    
    logger.info("Example completed") 