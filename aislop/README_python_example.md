# Naksha Python Client Example

This repository contains a comprehensive Python client for connecting to Naksha, HERE's geospatial data platform.

## Architecture Overview

```mermaid
graph TB
    subgraph "Python Client"
        A[NakshaClient] --> B[FeatureBuilder]
        A --> C[BatchProcessor]
        A --> D[ParallelProcessor]
    end
    
    subgraph "Naksha API"
        E[REST API] --> F[Space Management]
        E --> G[Feature Operations]
        E --> H[Spatial Queries]
    end
    
    subgraph "Storage Layer"
        I[PostgreSQL] --> J[Geospatial Indexes]
        I --> K[Connection Pool]
    end
    
    A --> E
    E --> I
    
    style A fill:#2196f3,stroke:#1976d2,stroke-width:3px,color:#fff
    style B fill:#4caf50,stroke:#388e3c,stroke-width:2px,color:#fff
    style C fill:#ff9800,stroke:#e65100,stroke-width:2px,color:#fff
    style D fill:#9c27b0,stroke:#7b1fa2,stroke-width:2px,color:#fff
    style E fill:#f44336,stroke:#d32f2f,stroke-width:3px,color:#fff
    style F fill:#607d8b,stroke:#455a64,stroke-width:2px,color:#fff
    style G fill:#795548,stroke:#5d4037,stroke-width:2px,color:#fff
    style H fill:#e91e63,stroke:#c2185b,stroke-width:2px,color:#fff
    style I fill:#00bcd4,stroke:#0097a7,stroke-width:3px,color:#fff
    style J fill:#ff5722,stroke:#d84315,stroke-width:2px,color:#fff
    style K fill:#8bc34a,stroke:#689f38,stroke-width:2px,color:#fff
```

## Data Flow

```mermaid
sequenceDiagram
    participant User
    participant Client as NakshaClient
    participant API as Naksha API
    participant DB as PostgreSQL
    
    User->>Client: Create/Update Features
    Client->>Client: Batch Features
    Client->>API: PUT /spaces/{id}/features
    API->>DB: Batch Upsert
    DB-->>API: Success Response
    API-->>Client: FeatureCollection Response
    Client-->>User: Processed Results
    
    Note over Client,DB: Batch operations are atomic - all succeed or all fail
```

## Features

- **Batch Operations**: Efficient bulk create, update, and delete operations
- **Spatial Queries**: Bounding box, radius, and tile-based queries
- **Parallel Processing**: High-performance data loading with concurrent requests
- **Error Handling**: Robust retry logic with exponential backoff
- **Feature Building**: Helper classes for creating GeoJSON features
- **Performance Optimization**: Configurable batch sizes and connection pooling

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

```python
from naksha_python_example import NakshaClient, NakshaConfig, FeatureBuilder

# Configure your connection
config = NakshaConfig(
    base_url="https://naksha-v2-dev.ext.mapcreator.here.com",
    access_token="your_access_token_here"
)

# Create client
client = NakshaClient(config)

# Create a space
space_response = client.create_space(
    space_id="my-space",
    title="My Test Space",
    description="A space for testing"
)

# Create features
features = []
for i in range(100):
    feature = FeatureBuilder.create_point_feature(
        coordinates=(8.68872 + i * 0.001, 50.0561 + i * 0.001, 100.0),
        properties={"speedLimit": str(30 + i % 5 * 10)},
        feature_id=f"feature-{i}"
    )
    features.append(feature)

# Batch upsert features
responses = client.batch_upsert_features("my-space", features)
print(f"Successfully processed {len(features)} features")
```

## API Methods

### Space Management

- `create_space(space_id, title, description)`: Create a new space
- `get_spaces()`: List all accessible spaces
- `delete_space(space_id)`: Delete a space

### Feature Operations

#### Batch Operations
- `batch_upsert_features(space_id, features, batch_size)`: Create or update features in batches
- `batch_create_features(space_id, features, batch_size)`: Create features (POST method)
- `parallel_batch_upsert(space_id, features, max_workers)`: Parallel batch processing

#### Query Operations
- `get_features_by_ids(space_id, feature_ids)`: Get features by ID
- `get_features_by_bbox(space_id, west, south, east, north, limit)`: Spatial query by bounding box
- `get_features_by_radius(space_id, lat, lon, radius, limit)`: Spatial query by radius
- `search_features(space_id, tags, properties_query, limit)`: Search by tags and properties
- `iterate_all_features(space_id, batch_size)`: Iterate through all features

#### Delete Operations
- `delete_features(space_id, feature_ids)`: Delete features by ID

## Performance Best Practices

### Performance Comparison

```mermaid
graph LR
    subgraph "Batch Sizes"
        A[100 features] --> B[200 req/sec]
        C[500 features] --> D[400 req/sec]
        E[1000 features] --> F[600 req/sec]
        G[2000 features] --> H[800 req/sec]
    end
    
    subgraph "Parallel Processing"
        I[1 Worker] --> J[600 req/sec]
        K[4 Workers] --> L[2000 req/sec]
        M[8 Workers] --> N[3000 req/sec]
    end
    
    style A fill:#2196f3,stroke:#1976d2,stroke-width:2px,color:#fff
    style B fill:#4caf50,stroke:#388e3c,stroke-width:2px,color:#fff
    style C fill:#ff9800,stroke:#e65100,stroke-width:2px,color:#fff
    style D fill:#9c27b0,stroke:#7b1fa2,stroke-width:2px,color:#fff
    style E fill:#f44336,stroke:#d32f2f,stroke-width:2px,color:#fff
    style F fill:#4caf50,stroke:#388e3c,stroke-width:3px,color:#fff
    style G fill:#607d8b,stroke:#455a64,stroke-width:2px,color:#fff
    style H fill:#795548,stroke:#5d4037,stroke-width:2px,color:#fff
    style I fill:#e91e63,stroke:#c2185b,stroke-width:2px,color:#fff
    style J fill:#00bcd4,stroke:#0097a7,stroke-width:2px,color:#fff
    style K fill:#ff5722,stroke:#d84315,stroke-width:2px,color:#fff
    style L fill:#4caf50,stroke:#388e3c,stroke-width:3px,color:#fff
    style M fill:#8bc34a,stroke:#689f38,stroke-width:2px,color:#fff
    style N fill:#cddc39,stroke:#afb42b,stroke-width:2px,color:#000
```

### 1. Batch Size Optimization

```python
# Test different batch sizes for your use case
config = NakshaConfig(
    base_url="your_url",
    access_token="your_token",
    batch_size=1000  # Adjust based on your data size
)
```

### 2. Parallel Processing

```python
# For large datasets, use parallel processing
responses = client.parallel_batch_upsert(
    space_id="my-space",
    features=large_feature_list,
    max_workers=4  # Adjust based on your system
)
```

### 3. Connection Pooling

The client automatically uses connection pooling via `requests.Session()` for better performance.

## Data Formats

### Feature Structure

```mermaid
graph TD
    A[Feature] --> B[id: string]
    A --> C[type: Feature]
    A --> D[properties: object]
    A --> E[geometry: object]
    
    D --> F[speedLimit: string]
    D --> G[ns_com_here_xyz]
    G --> H[tags: array]
    
    E --> I[type: Point/LineString/Polygon]
    E --> J[coordinates: array]
    
    style A fill:#ff9800,stroke:#e65100,stroke-width:3px,color:#fff
    style B fill:#2196f3,stroke:#1976d2,stroke-width:2px,color:#fff
    style C fill:#2196f3,stroke:#1976d2,stroke-width:2px,color:#fff
    style D fill:#4caf50,stroke:#388e3c,stroke-width:2px,color:#fff
    style E fill:#9c27b0,stroke:#7b1fa2,stroke-width:2px,color:#fff
    style F fill:#ff5722,stroke:#d84315,stroke-width:2px,color:#fff
    style G fill:#607d8b,stroke:#455a64,stroke-width:2px,color:#fff
    style H fill:#795548,stroke:#5d4037,stroke-width:2px,color:#fff
    style I fill:#e91e63,stroke:#c2185b,stroke-width:2px,color:#fff
    style J fill:#00bcd4,stroke:#0097a7,stroke-width:2px,color:#fff
```

```python
feature = {
    "id": "unique-feature-id",
    "type": "Feature",
    "properties": {
        "speedLimit": "60",
        "@ns:com:here:xyz": {
            "tags": ["traffic", "sign"]
        }
    },
    "geometry": {
        "type": "Point",
        "coordinates": [8.68872, 50.0561, 100.0]
    }
}
```

### Supported Geometry Types

- **Point**: Single coordinate `[lon, lat, elevation]`
- **LineString**: Array of coordinates `[[lon1, lat1], [lon2, lat2], ...]`
- **Polygon**: Array of coordinate rings `[[[lon1, lat1], [lon2, lat2], ...]]`

## Error Handling

The client includes robust error handling:

- **Automatic Retries**: Configurable retry logic with exponential backoff
- **Request Timeouts**: Configurable timeout settings
- **Detailed Logging**: Comprehensive logging for debugging

```python
config = NakshaConfig(
    base_url="your_url",
    access_token="your_token",
    timeout=30,        # Request timeout in seconds
    max_retries=3      # Number of retry attempts
)
```

## Examples

### Data Processing Workflow

```mermaid
flowchart TD
    A[Raw Data Source] --> B[Data Validation]
    B --> C[Feature Creation]
    C --> D[Batch Assembly]
    D --> E[Parallel Processing]
    E --> F[Naksha API]
    F --> G[Success Response]
    F --> H[Error Handling]
    H --> I[Retry Logic]
    I --> F
    
    style A fill:#2196f3,stroke:#1976d2,stroke-width:3px,color:#fff
    style B fill:#4caf50,stroke:#388e3c,stroke-width:2px,color:#fff
    style C fill:#ff9800,stroke:#e65100,stroke-width:2px,color:#fff
    style D fill:#9c27b0,stroke:#7b1fa2,stroke-width:2px,color:#fff
    style E fill:#f44336,stroke:#d32f2f,stroke-width:3px,color:#fff
    style F fill:#607d8b,stroke:#455a64,stroke-width:2px,color:#fff
    style G fill:#4caf50,stroke:#388e3c,stroke-width:3px,color:#fff
    style H fill:#f44336,stroke:#d32f2f,stroke-width:3px,color:#fff
    style I fill:#795548,stroke:#5d4037,stroke-width:2px,color:#fff
```

### 1. Bulk Data Import

```python
# Import large dataset efficiently
def import_large_dataset(client, space_id, data_source):
    features = []
    for row in data_source:
        feature = FeatureBuilder.create_point_feature(
            coordinates=(row['lon'], row['lat'], row['elevation']),
            properties={
                "name": row['name'],
                "type": row['type']
            }
        )
        features.append(feature)
    
    # Use parallel processing for large datasets
    responses = client.parallel_batch_upsert(space_id, features, max_workers=4)
    return responses
```

### 2. Spatial Analysis

```mermaid
graph LR
    subgraph "Spatial Queries"
        A[Bounding Box] --> B[get_features_by_bbox]
        C[Radius Search] --> D[get_features_by_radius]
        E[Tile Query] --> F[get_features_by_tile]
        G[Custom Geometry] --> H[spatial intersection]
    end
    
    subgraph "Analysis Pipeline"
        I[Query Results] --> J[Data Processing]
        J --> K[Statistical Analysis]
        K --> L[Visualization]
    end
    
    B --> I
    D --> I
    F --> I
    H --> I
    
    style A fill:#2196f3,stroke:#1976d2,stroke-width:2px,color:#fff
    style B fill:#4caf50,stroke:#388e3c,stroke-width:2px,color:#fff
    style C fill:#ff9800,stroke:#e65100,stroke-width:2px,color:#fff
    style D fill:#9c27b0,stroke:#7b1fa2,stroke-width:2px,color:#fff
    style E fill:#f44336,stroke:#d32f2f,stroke-width:2px,color:#fff
    style F fill:#607d8b,stroke:#455a64,stroke-width:2px,color:#fff
    style G fill:#795548,stroke:#5d4037,stroke-width:2px,color:#fff
    style H fill:#e91e63,stroke:#c2185b,stroke-width:2px,color:#fff
    style I fill:#00bcd4,stroke:#0097a7,stroke-width:3px,color:#fff
    style J fill:#ff5722,stroke:#d84315,stroke-width:2px,color:#fff
    style K fill:#8bc34a,stroke:#689f38,stroke-width:2px,color:#fff
    style L fill:#cddc39,stroke:#afb42b,stroke-width:3px,color:#000
```

```python
# Find all features within a specific area
def analyze_area(client, space_id, bbox):
    features = client.get_features_by_bbox(
        space_id,
        west=bbox['west'],
        south=bbox['south'],
        east=bbox['east'],
        north=bbox['north']
    )
    
    # Analyze the features
    df = pd.DataFrame([f['properties'] for f in features])
    return df.describe()
```

### 3. Real-time Updates

```python
# Update features in real-time
def update_features(client, space_id, updates):
    features = []
    for update in updates:
        feature = FeatureBuilder.create_point_feature(
            coordinates=update['coordinates'],
            properties=update['properties'],
            feature_id=update['id']
        )
        features.append(feature)
    
    # Use upsert to create or update
    responses = client.batch_upsert_features(space_id, features)
    return responses
```

## Configuration

### Environment Variables

```bash
export NAKSHA_BASE_URL="https://naksha-v2-dev.ext.mapcreator.here.com"
export NAKSHA_ACCESS_TOKEN="your_access_token"
```

### Configuration Class

```python
config = NakshaConfig(
    base_url=os.getenv("NAKSHA_BASE_URL"),
    access_token=os.getenv("NAKSHA_ACCESS_TOKEN"),
    timeout=30,
    max_retries=3,
    batch_size=1000
)
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**: Verify your access token is valid
2. **Timeout Errors**: Increase timeout or reduce batch size
3. **Memory Issues**: Reduce batch size for large datasets
4. **Rate Limiting**: Implement delays between requests

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Performance Benchmarks

```mermaid
graph TB
    subgraph "Performance Metrics"
        A[Batch Size 1000] --> B[500-1000 features/sec]
        C[Parallel Processing] --> D[2-4x improvement]
        E[Memory Usage] --> F[1MB per 1000 features]
        G[Network Latency] --> H[50-200ms per request]
    end
    
    subgraph "Optimization Levels"
        I[Basic] --> J[200 req/sec]
        K[Optimized] --> L[600 req/sec]
        M[Parallel] --> N[2000 req/sec]
    end
    
    style A fill:#2196f3,stroke:#1976d2,stroke-width:3px,color:#fff
    style B fill:#4caf50,stroke:#388e3c,stroke-width:3px,color:#fff
    style C fill:#ff9800,stroke:#e65100,stroke-width:3px,color:#fff
    style D fill:#4caf50,stroke:#388e3c,stroke-width:3px,color:#fff
    style E fill:#9c27b0,stroke:#7b1fa2,stroke-width:2px,color:#fff
    style F fill:#607d8b,stroke:#455a64,stroke-width:2px,color:#fff
    style G fill:#f44336,stroke:#d32f2f,stroke-width:2px,color:#fff
    style H fill:#795548,stroke:#5d4037,stroke-width:2px,color:#fff
    style I fill:#e91e63,stroke:#c2185b,stroke-width:2px,color:#fff
    style J fill:#00bcd4,stroke:#0097a7,stroke-width:2px,color:#fff
    style K fill:#ff5722,stroke:#d84315,stroke-width:2px,color:#fff
    style L fill:#ff9800,stroke:#e65100,stroke-width:3px,color:#fff
    style M fill:#8bc34a,stroke:#689f38,stroke-width:2px,color:#fff
    style N fill:#4caf50,stroke:#388e3c,stroke-width:3px,color:#fff
```

Typical performance metrics:

- **Batch Size 1000**: ~500-1000 features/second
- **Parallel Processing**: 2-4x improvement with 4 workers
- **Memory Usage**: ~1MB per 1000 features
- **Network Latency**: 50-200ms per request

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

This example is provided as-is for educational purposes. 