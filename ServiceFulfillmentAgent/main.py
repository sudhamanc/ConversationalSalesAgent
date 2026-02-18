"""
Main entry point for testing the Service Fulfillment Agent standalone.
"""

import os
from dotenv import load_dotenv
from service_fulfillment_agent import get_agent
from service_fulfillment_agent.utils.logger import get_logger

# Load environment variables
load_dotenv()

logger = get_logger(__name__)


def main():
    """Run the Service Fulfillment Agent in standalone mode for testing."""
    
    logger.info("Starting Service Fulfillment Agent in standalone mode...")
    
    # Get the agent instance
    agent = get_agent()
    
    print("\n" + "="*70)
    print("SERVICE FULFILLMENT AGENT - STANDALONE TEST MODE")
    print("="*70)
    print("\nThis agent handles service fulfillment for B2B telecommunications.")
    print("\nExample queries:")
    print("  - 'Schedule installation for 123 Main St'")
    print("  - 'What time slots are available next week?'")
    print("  - 'Check the status of order #12345'")
    print("  - 'Track equipment for installation'")
    print("  - 'Activate service for customer ABC Corp'")
    print("\nType 'quit' or 'exit' to stop.\n")
    
    # Interactive loop
    while True:
        try:
            user_input = input("You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\nExiting Service Fulfillment Agent. Goodbye!")
                break
            
            if not user_input:
                continue
            
            # Send message to agent
            logger.info(f"User input: {user_input}")
            response = agent.run(user_input)
            
            # Display response
            print(f"\nAgent: {response}\n")
            logger.info(f"Agent response: {response}")
            
        except KeyboardInterrupt:
            print("\n\nInterrupted. Exiting...")
            break
        except Exception as e:
            logger.error(f"Error processing request: {e}", exc_info=True)
            print(f"\nError: {str(e)}\n")
    
    logger.info("Service Fulfillment Agent session ended.")


if __name__ == "__main__":
    main()
