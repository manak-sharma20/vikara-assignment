import os
import yaml
import uuid
import groq
from datetime import datetime
from retrieval.rag import KnowledgeBase, format_context
from handover.protocol import HandoverLog, Handover
from agents.triage import get_triage_prompt
from agents.technical import get_technical_prompt
from agents.billing import get_billing_prompt
from agents.escalation import get_escalation_prompt

class Orchestrator:
    """The brain of the system tying agents, RAG, and memory together."""
    
    def __init__(self):
        self.kb = KnowledgeBase()
        self.conversation_history = []
        self.current_agent = "triage"
        self.customer_id = str(uuid.uuid4())
        self.trace_id = self.customer_id
        self.handover_log = HandoverLog()
        self.client = groq.Groq(api_key=os.getenv("GROQ_API_KEY", ""))
        
        # Load agents configuration
        with open("config/agents.yaml", "r") as f:
            self.agents_config = yaml.safe_load(f)["agents"]

    def classify_intent(self, message: str) -> str:
        """Classifies the customer message intent."""
        prompt = f'Classify this customer support message as one of: technical, billing, account, general, escalation. Reply with just the one word.\n\nMessage: "{message}"'
        response = self.client.chat.completions.create(
            model="llama-3.1-8b-instant",
            max_tokens=10,
            temperature=0,
            messages=[{"role": "user", "content": prompt}]
        )
        # Clean the output just in case
        return response.choices[0].message.content.strip().lower()

    def route_to_agent(self, intent: str) -> str:
        """Maps an intent to an agent name."""
        if "technical" in intent:
            return "technical_support"
        elif "billing" in intent:
            return "billing"
        elif "escalation" in intent:
            return "escalation"
        else:
            return "triage"

    def get_agent_response(self, agent_name: str, user_message: str) -> str:
        """Gets a response from the designated agent."""
        # Look up system prompt
        system_prompt = self.agents_config.get(agent_name, {}).get("system_prompt", "")
        
        # Search Knowledge Base
        kb_results = self.kb.search(user_message)
        kb_context = format_context(kb_results)
        
        # Get specialized prompt from the respective agent module
        if agent_name == "technical_support":
            agent_prompt = get_technical_prompt(kb_context, self.conversation_history)
        elif agent_name == "billing":
            agent_prompt = get_billing_prompt(kb_context, self.conversation_history)
        elif agent_name == "escalation":
            agent_prompt = get_escalation_prompt(kb_context, self.conversation_history)
        else:
            agent_prompt = get_triage_prompt(kb_context, self.conversation_history)
            
        full_system_prompt = f"{system_prompt}\n\n{agent_prompt}"
        
        # Call Groq
        # We pass the conversation history and the new message
        messages = [{"role": "system", "content": full_system_prompt}]
        messages.extend(self.conversation_history)
        
        response = self.client.chat.completions.create(
            model="llama-3.1-8b-instant",
            max_tokens=500,
            temperature=0.3,
            messages=messages
        )
        return response.choices[0].message.content

    def handle_handover(self, from_agent: str, to_agent: str, reason: str):
        """Logs a handover and updates the current agent."""
        if from_agent == to_agent:
            return
            
        summary = f"User needs {reason} assistance."
        if self.conversation_history:
            summary = self.conversation_history[-1]["content"][:100] + "..."
            
        handover = Handover(
            timestamp=datetime.utcnow().isoformat() + "Z",
            source_agent=from_agent,
            target_agent=to_agent,
            reason=reason,
            customer_id=self.customer_id,
            conversation_summary=summary
        )
        self.handover_log.log(handover)
        self.current_agent = to_agent

    def check_input(self, message: str) -> tuple[bool, str]:
        """Checks input for prompt injections."""
        banned = ["ignore previous instructions", "you are now", "forget your instructions"]
        for phrase in banned:
            if phrase in message.lower():
                return False, "Message contains forbidden phrases."
        return True, ""

    def check_output(self, response: str, kb_results: list) -> str:
        """Appends a pricing verification warning if pricing is mentioned but not in KB."""
        if "$" in response:
            kb_text = " ".join([res["content"] for res in kb_results])
            if "$" not in kb_text:
                return response + "\n\n⚠️ Note: Please verify pricing details at clouddash.io/pricing"
        return response

    def chat(self, user_message: str) -> str:
        """Main entry point for chatting with the system."""
        # Guardrails Step 11: input check
        is_safe, reason = self.check_input(user_message)
        if not is_safe:
            return f"Error: {reason}"
            
        # 1. Append user message to history
        # (Wait, if we append it here, then get_agent_response shouldn't append it again.
        # So in get_agent_response we just pass self.conversation_history)
        
        # Actually, let's append it now so the whole history is up to date
        self.conversation_history.append({"role": "user", "content": user_message})
        
        # 2. Classify intent
        intent = self.classify_intent(user_message)
        
        # 3. Route to the right agent
        target_agent = self.route_to_agent(intent)
        
        if target_agent != self.current_agent:
            self.handle_handover(self.current_agent, target_agent, intent)
            
        # 4. Get response
        # Let's search KB here as well for the check_output
        kb_results = self.kb.search(user_message)
        response_text = self.get_agent_response(self.current_agent, user_message)
        
        # 5. Guardrails Step 11: output check
        response_text = self.check_output(response_text, kb_results)
        
        # 6. Append assistant response
        self.conversation_history.append({"role": "assistant", "content": response_text})
        
        # 7. Return response
        return response_text
