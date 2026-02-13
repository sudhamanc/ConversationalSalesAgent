"""
Main entry point for testing the Payment Agent standalone.
"""

import os
from dotenv import load_dotenv
from payment_agent import get_agent
from payment_agent.utils.logger import get_logger

# Load environment variables
load_dotenv()

logger = get_logger(__name__)


def main():
    """Run the Payment Agent in standalone mode for testing."""
    
    logger.info("Starting Payment Agent in standalone mode...")
    
    # Get the agent instance
    agent = get_agent()
    
    print("\n" + "="*70)
    print("PAYMENT AGENT - STANDALONE TEST MODE")
    print("="*70)
    print("\nThis agent handles payment operations for B2B telecommunications.")
    print("\nExample queries:")
    print("  - 'I want to pay with a credit card'")
    print("  - 'Can you run a credit check for my business?'")
    print("  - 'What payment methods do you accept?'")
    print("  - 'Generate an invoice for the order'")
    print("\nType 'quit' or 'exit' to stop.\n")
    
    # Interactive loop
    while True:
        try:
            user_input = input("You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\nExiting Payment Agent. Goodbye!")
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
    
    logger.info("Payment Agent session ended.")


if __name__ == "__main__":
    main()
