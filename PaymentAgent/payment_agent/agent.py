"""Payment agent service - payment method setup, payment processing, credit checks, billing.

The gateway workflow engages this agent after installation scheduling with an explicit
message such as "Installation is scheduled for order <id>; total <amount>. Start payment."
(this replaces the legacy SuperAgent ``after_agent_callback`` payment opener).
"""

from typing import Optional

from google.adk import Agent
from google.adk.models.base_llm import BaseLlm

from sales_common.config import generate_config, model_name
from sales_common.models import agent_model
from sales_common.context import export_context_delta, import_forwarded_context
from sales_common.prompts import JOURNEY_CONTEXT_INSTRUCTION

from .prompts import PAYMENT_AGENT_INSTRUCTION, PAYMENT_SHORT_DESCRIPTION
from .tools.billing_tools import generate_invoice, get_payment_history, setup_payment_plan
from .tools.credit_tools import check_business_credit, get_credit_report
from .tools.payment_tools import (
    add_payment_method,
    get_payment_methods,
    process_payment,
    tokenize_payment_method,
    validate_payment_method,
)


def build_agent(model: Optional[str | BaseLlm] = None) -> Agent:
    """Build the payment_agent."""
    return Agent(
        name="payment_agent",
        model=model or agent_model(),
        description=PAYMENT_SHORT_DESCRIPTION,
        static_instruction=PAYMENT_AGENT_INSTRUCTION,
        instruction=JOURNEY_CONTEXT_INSTRUCTION,
        tools=[
            # Payment processing
            validate_payment_method,
            process_payment,
            get_payment_methods,
            tokenize_payment_method,
            add_payment_method,
            # Credit checks
            check_business_credit,
            get_credit_report,
            # Billing
            generate_invoice,
            get_payment_history,
            setup_payment_plan,
        ],
        before_agent_callback=[import_forwarded_context],
        after_tool_callback=[export_context_delta],
        generate_content_config=generate_config(temperature=0.0, max_output_tokens=2048),
    )


root_agent = build_agent()
