#!/usr/bin/env python3
"""
Naksha JAR Python Setup Script
===============================

This script helps set up and test the Naksha JAR Python example.

Usage:
    python setup_naksha_jar.py
"""

import os
import sys
import subprocess
import json
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        logger.error("Python 3.8+ is required")
        return False
    logger.info(f"Python version: {sys.version}")
    return True


def check_java_installation():
    """Check if Java is installed and has correct version"""
    try:
        result = subprocess.run(['java', '-version'], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error("Java is not installed or not in PATH")
            return False
        
        # Parse Java version
        version_output = result.stderr
        if 'version "17' in version_output or 'version "18' in version_output or 'version "19' in version_output or 'version "20' in version_output or 'version "21' in version_output:
            logger.info("Java 17+ is installed")
            return True
        else:
            logger.error("Java 17+ is required")
            return False
    except FileNotFoundError:
        logger.error("Java is not installed")
        return False


def check_postgresql_connection(host="localhost", port=5432, database="postgres", user="postgres", password="password"):
    """Check PostgreSQL connection"""
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        conn.close()
        logger.info("PostgreSQL connection successful")
        return True
    except ImportError:
        logger.error("psycopg2 is not installed. Install with: pip install psycopg2-binary")
        return False
    except Exception as e:
        logger.error(f"PostgreSQL connection failed: {e}")
        return False


def install_python_dependencies():
    """Install Python dependencies"""
    try:
        logger.info("Installing Python dependencies...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements_jar.txt'], check=True)
        logger.info("Python dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install Python dependencies: {e}")
        return False


def find_naksha_jar():
    """Find Naksha JAR file"""
    possible_paths = [
        "naksha-2.0.6-all.jar",
        "build/libs/naksha-2.0.6-all.jar",
        "../naksha/build/libs/naksha-2.0.6-all.jar",
        "naksha.jar"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            logger.info(f"Found Naksha JAR: {path}")
            return path
    
    logger.error("Naksha JAR not found. Please build it first:")
    logger.error("1. Clone Naksha repository")
    logger.error("2. Run: ./gradlew shadowJar")
    logger.error("3. Copy the JAR to this directory")
    return None


def create_config_file():
    """Create a sample configuration file"""
    config = {
        "jar_path": "naksha-2.0.6-all.jar",
        "database_url": "jdbc:postgresql://localhost:5432/naksha_db?user=postgres&password=password&schema=naksha&app=naksha_local&id=naksha_admin_db",
        "app_name": "naksha-python-client",
        "config_id": "default-config"
    }
    
    with open('naksha_config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    logger.info("Created naksha_config.json with sample configuration")
    return config


def test_jpype_import():
    """Test JPype1 import and basic functionality"""
    try:
        import jpype
        logger.info("JPype1 imported successfully")
        
        # Test basic JVM functionality
        if not jpype.isJVMStarted():
            logger.info("JVM is not started (expected)")
        else:
            logger.info("JVM is already started")
        
        return True
    except ImportError:
        logger.error("JPype1 is not installed. Install with: pip install jpype1")
        return False
    except Exception as e:
        logger.error(f"JPype1 test failed: {e}")
        return False


def create_sample_script():
    """Create a sample script for testing"""
    sample_script = '''#!/usr/bin/env python3
"""
Sample Naksha JAR Python Script
===============================

This is a sample script to test the Naksha JAR Python integration.
"""

import json
import logging
from naksha_python_jar_example import NakshaJarClient, NakshaJarConfig, FeatureBuilder

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    # Load configuration
    with open('naksha_config.json', 'r') as f:
        config_dict = json.load(f)
    
    config = NakshaJarConfig(**config_dict)
    
    # Create client
    client = NakshaJarClient(config)
    
    try:
        # Create a test space
        logger.info("Creating test space...")
        space = client.create_space(
            space_id="test-space",
            title="Test Space",
            description="A test space created by the setup script"
        )
        logger.info(f"Space created: {space}")
        
        # Create some test features
        logger.info("Creating test features...")
        features = []
        for i in range(5):
            feature = FeatureBuilder.create_point_feature(
                coordinates=(8.68872 + i * 0.001, 50.0561 + i * 0.001, 100.0),
                properties={
                    "name": f"Test Point {i}",
                    "category": "test",
                    "value": i
                },
                feature_id=f"test-feature-{i}"
            )
            features.append(feature)
        
        # Create features
        created_features = client.create_features("test-space", features)
        logger.info(f"Created {len(created_features)} features")
        
        # Query features
        bbox_features = client.get_features_by_bbox(
            "test-space",
            west=8.688, south=50.056, east=8.690, north=50.058
        )
        logger.info(f"Found {len(bbox_features)} features in bbox")
        
        logger.info("Test completed successfully!")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise
    finally:
        client.close()

if __name__ == "__main__":
    main()
'''
    
    with open('test_naksha_jar.py', 'w') as f:
        f.write(sample_script)
    
    logger.info("Created test_naksha_jar.py sample script")


def main():
    """Main setup function"""
    logger.info("Naksha JAR Python Setup")
    logger.info("========================")
    
    # Check prerequisites
    checks_passed = True
    
    logger.info("Checking prerequisites...")
    
    if not check_python_version():
        checks_passed = False
    
    if not check_java_installation():
        checks_passed = False
    
    if not check_postgresql_connection():
        logger.warning("PostgreSQL connection failed. Please ensure PostgreSQL is running and accessible.")
        logger.warning("You can still proceed with the setup, but database operations will fail.")
    
    if not test_jpype_import():
        checks_passed = False
    
    # Install dependencies
    if not install_python_dependencies():
        checks_passed = False
    
    # Find JAR file
    jar_path = find_naksha_jar()
    if not jar_path:
        checks_passed = False
    
    # Create configuration
    config = create_config_file()
    
    # Create sample script
    create_sample_script()
    
    # Summary
    logger.info("")
    logger.info("Setup Summary")
    logger.info("=============")
    
    if checks_passed:
        logger.info("✅ All checks passed!")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Update naksha_config.json with your database settings")
        logger.info("2. Run: python test_naksha_jar.py")
        logger.info("3. Check the README_jar_example.md for detailed usage")
    else:
        logger.error("❌ Some checks failed. Please fix the issues above before proceeding.")
        logger.info("")
        logger.info("Common issues:")
        logger.info("- Install Java 17+: https://adoptium.net/")
        logger.info("- Install PostgreSQL: https://www.postgresql.org/download/")
        logger.info("- Build Naksha JAR: ./gradlew shadowJar")
        logger.info("- Install Python dependencies: pip install -r requirements_jar.txt")
    
    logger.info("")
    logger.info("Files created:")
    logger.info("- naksha_config.json: Configuration file")
    logger.info("- test_naksha_jar.py: Sample test script")
    logger.info("- requirements_jar.txt: Python dependencies")
    logger.info("- naksha_python_jar_example.py: Main example code")
    logger.info("- README_jar_example.md: Detailed documentation")


if __name__ == "__main__":
    main() 