"""Standalone script to run the LangGraph workflow"""

import logging
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.graph.workflow import run_workflow

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

if __name__ == "__main__":
    # Test objective - the same one that achieved 100/100 score
    objective = """
    Build a product pricing analysis system:
    
    1. Search the internet for "average smartphone prices 2025" and save findings to market_research.txt
    
    2. Create prices.py with a function calculate_discount(price, percent) that returns discounted price
    
    3. Create product_catalog.csv with 5 smartphones: name, original_price (between $500-$1200)
    
    4. Edit prices.py to ADD a function apply_bulk_discount(prices_list, discount_percent) that applies discount to all items
    
    5. Read product_catalog.csv and apply 15% discount using the functions from prices.py
    
    6. Generate final_report.txt that includes:
       - Market research findings
       - Original product catalog
       - Discounted prices
       - Total savings
       - Recommendation based on market research
    """
    
    print("🚀 Starting LangGraph Workflow")
    print("="*70)
    print(f"Objective: {objective.strip()}")
    print("="*70)
    
    try:
        result = run_workflow(objective, max_iterations=25)
        
        print("\n" + "="*70)
        print("🎯 FINAL RESULTS")
        print("="*70)
        print(f"Total iterations: {result['iteration_count']}")
        print(f"Tasks created: {len(result['todo_list'])}")
        print(f"Tasks completed: {len(result['completed_tasks'])}")
        
        if result['completed_tasks']:
            print(f"\n✅ Completed tasks:")
            for i, task in enumerate(result['completed_tasks'], 1):
                task_desc = task.get('task', 'Unknown')[:60]
                print(f"  {i}. {task_desc}...")
        
        if result.get('final_result'):
            print(f"\n📋 Final Result:")
            print(result['final_result'][:200] + "..." if len(result['final_result']) > 200 else result['final_result'])
        
        print("="*70)
        print("✅ Workflow completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error running workflow: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
