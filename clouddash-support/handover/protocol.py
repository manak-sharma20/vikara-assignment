import json
from pydantic import BaseModel

class Handover(BaseModel):
    """Pydantic model representing a handover event between agents."""
    timestamp: str
    source_agent: str
    target_agent: str
    reason: str
    customer_id: str
    conversation_summary: str

class HandoverLog:
    """Handles logging of agent handover events."""
    
    def __init__(self, log_file: str = "handover_log.jsonl"):
        self.log_file = log_file

    def log(self, handover: Handover) -> None:
        """Appends the handover event to a JSONL file and prints to console."""
        handover_json = handover.model_dump_json()
        
        # Append to jsonl file
        with open(self.log_file, "a") as f:
            f.write(handover_json + "\n")
            
        # Print to console
        print(f"--- HANDOVER LOGGED ---")
        print(f"From: {handover.source_agent} -> To: {handover.target_agent}")
        print(f"Reason: {handover.reason}")
        print(f"Customer: {handover.customer_id}")
        print("-----------------------")
