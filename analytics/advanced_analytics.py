#!/usr/bin/env python3
"""
Advanced Analytics Dashboard
============================

This script provides advanced analytics on our processed customer data,
including business intelligence, customer insights, and performance metrics.

Author: Data Pipeline Team
Version: 1.0.0
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
import pandas as pd
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from elasticsearch import Elasticsearch
    import matplotlib.pyplot as plt
    import seaborn as sns
except ImportError as e:
    logger.error(f"Missing dependencies: {e}")
    logger.error("Run: pip install elasticsearch matplotlib seaborn")
    exit(1)

class AdvancedAnalytics:
    """Advanced analytics for customer data."""
    
    def __init__(self):
        self.es = Elasticsearch(['http://localhost:9200'])
        self.index = 'customer_profiles'
        
    def get_all_profiles(self) -> List[Dict]:
        """Retrieve all customer profiles from Elasticsearch."""
        try:
            # Use scroll API for large datasets
            profiles = []
            query = {"query": {"match_all": {}}}
            
            response = self.es.search(
                index=self.index,
                body=query,
                scroll='2m',
                size=1000
            )
            
            scroll_id = response['_scroll_id']
            hits = response['hits']['hits']
            
            while hits:
                for hit in hits:
                    profiles.append(hit['_source'])
                
                response = self.es.scroll(
                    scroll_id=scroll_id,
                    scroll='2m'
                )
                scroll_id = response['_scroll_id']
                hits = response['hits']['hits']
            
            logger.info(f"Retrieved {len(profiles)} customer profiles")
            return profiles
            
        except Exception as e:
            logger.error(f"Failed to retrieve profiles: {e}")
            return []
    
    def generate_business_intelligence(self, profiles: List[Dict]) -> Dict:
        """Generate comprehensive business intelligence."""
        logger.info("🔍 Generating Business Intelligence Report...")
        
        if not profiles:
            return {}
        
        df = pd.DataFrame(profiles)
        
        # Basic metrics
        total_customers = len(df)
        total_revenue = df['total_revenue'].sum()
        total_purchases = df['total_purchases'].sum()
        
        # Customer segment analysis
        segment_analysis = df.groupby('customer_segment').agg({
            'user_id': 'count',
            'total_revenue': ['sum', 'mean'],
            'total_purchases': ['sum', 'mean'],
            'conversion_rate': 'mean'
        }).round(2)
        
        # Revenue distribution
        revenue_stats = {
            'total_revenue': total_revenue,
            'avg_customer_value': total_revenue / total_customers,
            'median_customer_value': df['total_revenue'].median(),
            'top_10_percent_revenue': df.nlargest(int(total_customers * 0.1), 'total_revenue')['total_revenue'].sum()
        }
        
        # Purchase behavior
        purchase_stats = {
            'total_purchases': total_purchases,
            'customers_with_purchases': len(df[df['total_purchases'] > 0]),
            'avg_purchases_per_customer': total_purchases / total_customers,
            'conversion_rate': (len(df[df['total_purchases'] > 0]) / total_customers) * 100
        }
        
        # Engagement metrics
        engagement_stats = {
            'avg_events_per_customer': df['total_events'].mean(),
            'avg_sessions_per_customer': df['total_sessions'].mean(),
            'high_engagement_customers': len(df[df['total_events'] > df['total_events'].quantile(0.8)])
        }
        
        return {
            'overview': {
                'total_customers': total_customers,
                'analysis_date': datetime.now().isoformat()
            },
            'revenue_analysis': revenue_stats,
            'purchase_behavior': purchase_stats,
            'engagement_metrics': engagement_stats,
            'segment_analysis': segment_analysis.to_dict()
        }
    
    def identify_customer_insights(self, profiles: List[Dict]) -> Dict:
        """Generate actionable customer insights."""
        logger.info("💡 Generating Customer Insights...")
        
        df = pd.DataFrame(profiles)
        
        insights = {
            'high_value_opportunities': [],
            'at_risk_customers': [],
            'conversion_opportunities': [],
            'retention_strategies': []
        }
        
        # High-value opportunities (high engagement, low spend)
        high_engagement = df[df['total_events'] > df['total_events'].quantile(0.8)]
        low_spend = high_engagement[high_engagement['total_revenue'] < df['total_revenue'].mean()]
        
        insights['high_value_opportunities'] = [
            f"{len(low_spend)} highly engaged customers with low spend",
            f"Average events: {low_spend['total_events'].mean():.0f}",
            f"Average revenue: ${low_spend['total_revenue'].mean():.2f}",
            "Recommendation: Target with personalized offers"
        ]
        
        # Conversion opportunities (cart additions but no purchases)
        cart_no_purchase = df[(df['total_cart_additions'] > 0) & (df['total_purchases'] == 0)]
        
        insights['conversion_opportunities'] = [
            f"{len(cart_no_purchase)} customers added items to cart but didn't purchase",
            f"Average cart additions: {cart_no_purchase['total_cart_additions'].mean():.1f}",
            "Recommendation: Abandoned cart email campaigns"
        ]
        
        # Active browsers (many views, no engagement)
        browsers = df[(df['total_product_views'] > 10) & (df['total_purchases'] == 0) & (df['total_cart_additions'] == 0)]
        
        insights['retention_strategies'] = [
            f"{len(browsers)} active browsers with no conversion",
            f"Average product views: {browsers['total_product_views'].mean():.0f}",
            "Recommendation: Retargeting campaigns with incentives"
        ]
        
        return insights
    
    def generate_performance_metrics(self) -> Dict:
        """Generate system performance metrics."""
        logger.info("⚡ Analyzing System Performance...")
        
        try:
            # Elasticsearch cluster health
            cluster_health = self.es.cluster.health()
            
            # Index statistics
            index_stats = self.es.indices.stats(index=self.index)
            
            performance = {
                'elasticsearch_health': cluster_health['status'],
                'total_documents': index_stats['indices'][self.index]['total']['docs']['count'],
                'index_size': f"{index_stats['indices'][self.index]['total']['store']['size_in_bytes'] / 1024 / 1024:.2f} MB",
                'search_performance': {
                    'total_searches': index_stats['indices'][self.index]['total']['search']['query_total'],
                    'avg_search_time': f"{index_stats['indices'][self.index]['total']['search']['query_time_in_millis'] / max(1, index_stats['indices'][self.index]['total']['search']['query_total']):.2f}ms"
                }
            }
            
            return performance
            
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return {}
    
    def generate_recommendations(self, profiles: List[Dict], insights: Dict) -> List[str]:
        """Generate actionable business recommendations."""
        logger.info("📋 Generating Business Recommendations...")
        
        df = pd.DataFrame(profiles)
        recommendations = []
        
        # Revenue optimization
        casual_visitors = len(df[df['customer_segment'] == 'Casual Visitor'])
        total_customers = len(df)
        
        if casual_visitors / total_customers > 0.8:
            recommendations.append("🎯 High Priority: 80%+ customers are casual visitors - implement engagement campaigns")
        
        # Conversion rate optimization
        avg_conversion = (len(df[df['total_purchases'] > 0]) / total_customers) * 100
        if avg_conversion < 5:
            recommendations.append(f"🔄 Conversion Rate: {avg_conversion:.1f}% is low - A/B test checkout process improvements")
        
        # Customer value optimization
        avg_order_value = df[df['total_purchases'] > 0]['avg_order_value'].mean()
        if avg_order_value < 50:
            recommendations.append(f"💰 AOV: ${avg_order_value:.2f} - implement upselling strategies")
        
        # Retention strategies
        one_time_buyers = len(df[df['total_purchases'] == 1])
        if one_time_buyers > 0:
            recommendations.append(f"🔄 Retention: {one_time_buyers} one-time buyers - create loyalty programs")
        
        return recommendations
    
    def generate_comprehensive_report(self) -> None:
        """Generate and display comprehensive analytics report."""
        logger.info("📊 ADVANCED ANALYTICS DASHBOARD")
        logger.info("=" * 60)
        
        # Get data
        profiles = self.get_all_profiles()
        if not profiles:
            logger.error("No customer profiles found")
            return
        
        # Generate analytics
        business_intelligence = self.generate_business_intelligence(profiles)
        customer_insights = self.identify_customer_insights(profiles)
        performance_metrics = self.generate_performance_metrics()
        recommendations = self.generate_recommendations(profiles, customer_insights)
        
        # Display results
        self.display_report(business_intelligence, customer_insights, performance_metrics, recommendations)
    
    def display_report(self, bi: Dict, insights: Dict, performance: Dict, recommendations: List[str]):
        """Display formatted analytics report."""
        
        print("\n🏢 BUSINESS INTELLIGENCE OVERVIEW")
        print("-" * 40)
        if bi.get('overview'):
            print(f"Total Customers: {bi['overview']['total_customers']:,}")
            print(f"Analysis Date: {bi['overview']['analysis_date']}")
        
        print("\n💰 REVENUE ANALYSIS")
        print("-" * 40)
        if bi.get('revenue_analysis'):
            rev = bi['revenue_analysis']
            print(f"Total Revenue: ${rev.get('total_revenue', 0):,.2f}")
            print(f"Avg Customer Value: ${rev.get('avg_customer_value', 0):.2f}")
            print(f"Median Customer Value: ${rev.get('median_customer_value', 0):.2f}")
            print(f"Top 10% Customer Revenue: ${rev.get('top_10_percent_revenue', 0):,.2f}")
        
        print("\n🛒 PURCHASE BEHAVIOR")
        print("-" * 40)
        if bi.get('purchase_behavior'):
            pb = bi['purchase_behavior']
            print(f"Total Purchases: {pb.get('total_purchases', 0):,}")
            print(f"Converting Customers: {pb.get('customers_with_purchases', 0):,}")
            print(f"Overall Conversion Rate: {pb.get('conversion_rate', 0):.2f}%")
            print(f"Avg Purchases/Customer: {pb.get('avg_purchases_per_customer', 0):.2f}")
        
        print("\n👥 CUSTOMER SEGMENTS")
        print("-" * 40)
        if bi.get('segment_analysis'):
            for segment, data in bi['segment_analysis'].items():
                if isinstance(data, dict) and 'user_id' in data:
                    count = data['user_id']['count']
                    revenue = data['total_revenue']['sum']
                    print(f"{segment}: {count:,} customers (${revenue:,.2f} revenue)")
        
        print("\n💡 KEY INSIGHTS")
        print("-" * 40)
        for category, insight_list in insights.items():
            if insight_list:
                print(f"\n{category.replace('_', ' ').title()}:")
                for insight in insight_list:
                    print(f"  • {insight}")
        
        print("\n⚡ SYSTEM PERFORMANCE")
        print("-" * 40)
        if performance:
            print(f"Elasticsearch Health: {performance.get('elasticsearch_health', 'Unknown')}")
            print(f"Total Documents: {performance.get('total_documents', 0):,}")
            print(f"Index Size: {performance.get('index_size', 'Unknown')}")
        
        print("\n📋 BUSINESS RECOMMENDATIONS")
        print("-" * 40)
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. {rec}")
        
        print("\n" + "=" * 60)
        print("📊 Advanced Analytics Complete!")

def main():
    """Main execution function."""
    try:
        analytics = AdvancedAnalytics()
        analytics.generate_comprehensive_report()
    except KeyboardInterrupt:
        logger.info("Analysis interrupted by user")
    except Exception as e:
        logger.error(f"Analysis failed: {e}")

if __name__ == "__main__":
    main()
