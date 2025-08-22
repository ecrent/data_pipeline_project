#!/usr/bin/env python3
"""
Real-time Pipeline Monitoring Dashboard
=======================================

This script provides real-time monitoring of the entire data pipeline,
including Kafka ingestion, Spark processing, and data storage health.

Author: Data Pipeline Team  
Version: 1.0.0
"""

import time
import json
import logging
import subprocess
from datetime import datetime
from typing import Dict, List, Any
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from kafka import KafkaConsumer
    from kafka.admin import KafkaAdminClient
    from elasticsearch import Elasticsearch
    import requests
except ImportError as e:
    logger.error(f"Missing dependencies: {e}")
    logger.error("Run: pip install kafka-python elasticsearch requests")
    exit(1)

class PipelineMonitor:
    """Real-time pipeline monitoring and health checks."""
    
    def __init__(self):
        # Detect if we're in Codespaces
        import os
        self.is_codespaces = os.getenv('CODESPACE_NAME') is not None
        self.codespace_name = os.getenv('CODESPACE_NAME', '')
        
        if self.is_codespaces:
            base_url = f"https://{self.codespace_name}-{{port}}.app.github.dev"
            self.services = {
                'kafka': {'host': 'localhost', 'port': 9092, 'status': 'Unknown', 'type': 'tcp'},
                'spark-master': {'host': 'localhost', 'port': 8080, 'status': 'Unknown', 'type': 'http', 'url': base_url.format(port=8080)},
                'spark-worker': {'host': 'localhost', 'port': 8081, 'status': 'Unknown', 'type': 'http', 'url': base_url.format(port=8081)},
                'elasticsearch': {'host': 'localhost', 'port': 9200, 'status': 'Unknown', 'type': 'elasticsearch'},
                'kibana': {'host': 'localhost', 'port': 5601, 'status': 'Unknown', 'type': 'http', 'url': base_url.format(port=5601)},
                'minio': {'host': 'localhost', 'port': 9001, 'status': 'Unknown', 'type': 'http', 'url': base_url.format(port=9001)}
            }
        else:
            self.services = {
                'kafka': {'host': 'localhost', 'port': 9092, 'status': 'Unknown', 'type': 'tcp'},
                'spark-master': {'host': 'localhost', 'port': 8080, 'status': 'Unknown', 'type': 'http'},
                'spark-worker': {'host': 'localhost', 'port': 8081, 'status': 'Unknown', 'type': 'http'},
                'elasticsearch': {'host': 'localhost', 'port': 9200, 'status': 'Unknown', 'type': 'elasticsearch'},
                'kibana': {'host': 'localhost', 'port': 5601, 'status': 'Unknown', 'type': 'http'},
                'minio': {'host': 'localhost', 'port': 9001, 'status': 'Unknown', 'type': 'http'}
            }
        
    def check_service_health(self, service: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Check individual service health."""
        try:
            service_type = config.get('type', 'http')
            host = config['host']
            port = config['port']
            
            if service_type == 'elasticsearch':
                es = Elasticsearch([f'http://{host}:{port}'])
                health = es.cluster.health()
                return {
                    'status': 'Healthy' if health['status'] in ['green', 'yellow'] else 'Unhealthy',
                    'details': {
                        'cluster_status': health['status'],
                        'active_nodes': health['number_of_nodes'],
                        'active_shards': health['active_shards']
                    }
                }
            
            elif service_type == 'tcp' and service == 'kafka':
                # Simple socket connection test for Kafka
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex((host, port))
                sock.close()
                
                if result == 0:
                    return {
                        'status': 'Healthy',
                        'details': {'connection': 'TCP connection successful'}
                    }
                else:
                    return {
                        'status': 'Down',
                        'details': {'error': f'Cannot connect to {host}:{port}'}
                    }
            
            elif service_type == 'http':
                # Use Codespaces URL if available, otherwise localhost
                if self.is_codespaces and 'url' in config:
                    url = config['url']
                else:
                    url = f'http://{host}:{port}'
                
                response = requests.get(url, timeout=10)
                return {
                    'status': 'Healthy' if response.status_code == 200 else 'Degraded',
                    'details': {
                        'response_code': response.status_code,
                        'url': url if self.is_codespaces else f'{host}:{port}'
                    }
                }
                
        except Exception as e:
            return {
                'status': 'Down',
                'details': {'error': str(e)}
            }
    
    def get_kafka_metrics(self) -> Dict[str, Any]:
        """Get Kafka topic and consumer metrics."""
        try:
            # Simple socket test first
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(('localhost', 9092))
            sock.close()
            
            if result != 0:
                return {
                    'status': 'error',
                    'error': 'Cannot connect to Kafka broker'
                }
            
            # Try to get basic topic info using kafka-python
            from kafka.admin import KafkaAdminClient, NewTopic
            admin_client = KafkaAdminClient(
                bootstrap_servers=['localhost:9092'],
                client_id='health_check'
            )
            
            # List topics
            topic_metadata = admin_client.list_topics()
            topics = list(topic_metadata)
            
            admin_client.close()
            
            return {
                'connection_status': 'successful',
                'topics': topics,
                'raw_events_available': 'raw_events' in topics,
                'status': 'operational'
            }
        except Exception as e:
            return {
                'status': 'error', 
                'error': str(e)
            }
    
    def get_elasticsearch_metrics(self) -> Dict[str, Any]:
        """Get Elasticsearch index and document metrics."""
        try:
            es = Elasticsearch(['http://localhost:9200'])
            
            # Get cluster stats
            cluster_health = es.cluster.health()
            
            # Get index stats
            index_stats = es.indices.stats(index='customer_profiles')
            profiles_index = index_stats['indices']['customer_profiles']
            
            return {
                'cluster_status': cluster_health['status'],
                'total_documents': profiles_index['total']['docs']['count'],
                'index_size_mb': round(profiles_index['total']['store']['size_in_bytes'] / (1024 * 1024), 2),
                'search_queries_total': profiles_index['total']['search']['query_total'],
                'indexing_operations': profiles_index['total']['indexing']['index_total']
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def get_docker_container_status(self) -> Dict[str, Any]:
        """Get Docker container status for pipeline services."""
        try:
            result = subprocess.run(
                ['docker', 'ps', '--format', 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return {'error': 'Docker not accessible'}
            
            containers = {}
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            
            for line in lines:
                parts = line.split('\t')
                if len(parts) >= 2:
                    name = parts[0].strip()
                    status = parts[1].strip()
                    containers[name] = {
                        'status': status,
                        'ports': parts[2].strip() if len(parts) > 2 else 'N/A'
                    }
            
            return containers
        except Exception as e:
            return {'error': str(e)}
    
    def run_comprehensive_health_check(self) -> Dict[str, Any]:
        """Run comprehensive health check across all services."""
        logger.info("🔍 Running comprehensive pipeline health check...")
        
        health_report = {
            'timestamp': datetime.now().isoformat(),
            'services': {},
            'kafka_metrics': {},
            'elasticsearch_metrics': {},
            'docker_containers': {},
            'overall_status': 'Unknown'
        }
        
        # Check individual services
        healthy_services = 0
        total_services = len(self.services)
        
        for service_name, config in self.services.items():
            logger.info(f"Checking {service_name}...")
            health = self.check_service_health(service_name, config)
            health_report['services'][service_name] = health
            
            if health['status'] == 'Healthy':
                healthy_services += 1
        
        # Get detailed metrics
        health_report['kafka_metrics'] = self.get_kafka_metrics()
        health_report['elasticsearch_metrics'] = self.get_elasticsearch_metrics()
        health_report['docker_containers'] = self.get_docker_container_status()
        
        # Determine overall status
        if healthy_services == total_services:
            health_report['overall_status'] = 'All Systems Operational'
        elif healthy_services >= total_services * 0.8:
            health_report['overall_status'] = 'Most Systems Operational'
        elif healthy_services >= total_services * 0.5:
            health_report['overall_status'] = 'Partial System Outage'
        else:
            health_report['overall_status'] = 'Major System Outage'
        
        return health_report
    
    def display_health_dashboard(self, report: Dict[str, Any]):
        """Display formatted health dashboard."""
        print("\n" + "="*80)
        print("🔍 REAL-TIME PIPELINE MONITORING DASHBOARD")
        print("="*80)
        
        print(f"\n⏰ Report Time: {report['timestamp']}")
        print(f"🚦 Overall Status: {report['overall_status']}")
        
        print("\n🔧 SERVICE HEALTH STATUS")
        print("-" * 50)
        for service, health in report['services'].items():
            status_emoji = {
                'Healthy': '✅',
                'Degraded': '⚠️',
                'Down': '❌',
                'Unknown': '❓'
            }.get(health['status'], '❓')
            
            print(f"{status_emoji} {service}: {health['status']}")
            if 'details' in health and health['details']:
                for key, value in health['details'].items():
                    print(f"    {key}: {value}")
        
        print("\n📊 KAFKA METRICS")
        print("-" * 50)
        kafka_metrics = report['kafka_metrics']
        if 'error' not in kafka_metrics:
            print(f"Connection: {kafka_metrics.get('connection_status', 'N/A')}")
            print(f"Topics: {kafka_metrics.get('topics', [])}")
            print(f"Raw Events Topic: {'✅' if kafka_metrics.get('raw_events_available') else '❌'}")
            print(f"Status: {kafka_metrics.get('status', 'N/A')}")
        else:
            print(f"❌ Error: {kafka_metrics['error']}")
        
        print("\n🗄️  ELASTICSEARCH METRICS")
        print("-" * 50)
        es_metrics = report['elasticsearch_metrics']
        if 'error' not in es_metrics:
            print(f"Cluster Status: {es_metrics.get('cluster_status', 'N/A')}")
            print(f"Customer Profiles: {es_metrics.get('total_documents', 'N/A'):,}")
            print(f"Index Size: {es_metrics.get('index_size_mb', 'N/A')} MB")
            print(f"Search Queries: {es_metrics.get('search_queries_total', 'N/A'):,}")
            print(f"Indexing Operations: {es_metrics.get('indexing_operations', 'N/A'):,}")
        else:
            print(f"❌ Error: {es_metrics['error']}")
        
        print("\n🐳 DOCKER CONTAINERS")
        print("-" * 50)
        containers = report['docker_containers']
        if 'error' not in containers:
            for name, info in containers.items():
                if any(service in name.lower() for service in ['kafka', 'spark', 'elasticsearch', 'kibana', 'minio']):
                    status_emoji = '✅' if 'up' in info['status'].lower() else '❌'
                    print(f"{status_emoji} {name}: {info['status']}")
        else:
            print(f"❌ Error: {containers['error']}")
        
        print("\n" + "="*80)
    
    def continuous_monitoring(self, interval_seconds: int = 30):
        """Run continuous monitoring with specified interval."""
        logger.info(f"🔄 Starting continuous monitoring (every {interval_seconds}s)")
        logger.info("Press Ctrl+C to stop monitoring")
        
        try:
            while True:
                report = self.run_comprehensive_health_check()
                self.display_health_dashboard(report)
                
                print(f"\n⏳ Next check in {interval_seconds} seconds...")
                time.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            logger.info("🛑 Monitoring stopped by user")
        except Exception as e:
            logger.error(f"💥 Monitoring failed: {e}")

def main():
    """Main execution function."""
    monitor = PipelineMonitor()
    
    print("🔍 Data Pipeline Health Monitor")
    print("=" * 40)
    print("1. Run single health check")
    print("2. Continuous monitoring (30s intervals)")
    print("3. Quick monitoring (5s intervals)")
    
    choice = input("\nSelect option (1-3): ").strip()
    
    if choice == '1':
        report = monitor.run_comprehensive_health_check()
        monitor.display_health_dashboard(report)
    elif choice == '2':
        monitor.continuous_monitoring(30)
    elif choice == '3':
        monitor.continuous_monitoring(5)
    else:
        logger.info("Running single health check...")
        report = monitor.run_comprehensive_health_check()
        monitor.display_health_dashboard(report)

if __name__ == "__main__":
    main()
