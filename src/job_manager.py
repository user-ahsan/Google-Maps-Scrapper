import json
import os
import time

class JobManager:
    """
    Manages the state of a scraping job to allow for pausing and resuming.
    Saves state to a robust JSON file.
    """
    def __init__(self, state_file='job_state.json'):
        self.state_file = state_file
        self.current_state = {
            "job_id": None,
            "timestamp": None,
            "completed_queries": [],
            "pending_queries": [],
            "total_leads_found": 0,
            "status": "IDLE" # IDLE, RUNNING, PAUSED, COMPLETED
        }
        self.load_state()

    def load_state(self):
        """Loads state from disk if it exists."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    self.current_state = json.load(f)
            except Exception as e:
                print(f"Error loading job state: {e}")
                # If corrupt, we start fresh, keeping default current_state

    def save_state(self):
        """Saves current state to disk."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.current_state, f, indent=4)
        except Exception as e:
            print(f"Error saving job state: {e}")

    def start_new_job(self, queries):
        """Initializes a new job, overwriting previous state."""
        self.current_state = {
            "job_id": f"JOB-{int(time.time())}",
            "timestamp": time.time(),
            "completed_queries": [],
            "pending_queries": queries, # List of strings
            "total_leads_found": 0,
            "status": "RUNNING"
        }
        self.save_state()

    def mark_query_complete(self, query):
        """Moves a query from pending to completed."""
        if query in self.current_state["pending_queries"]:
            self.current_state["pending_queries"].remove(query)
        if query not in self.current_state["completed_queries"]:
            self.current_state["completed_queries"].append(query)
        self.save_state()

    def update_leads_count(self, count):
        """Updates the total leads found count."""
        self.current_state["total_leads_found"] += count
        self.save_state()

    def set_status(self, status):
        """Updates job status (e.g. PAUSED, COMPLETED)."""
        self.current_state["status"] = status
        self.save_state()

    def get_pending_queries(self):
        return self.current_state.get("pending_queries", [])

    def has_unfinished_job(self):
        """Returns True if there is a job that is not COMPLETED and has pending queries."""
        return (self.current_state["status"] != "COMPLETED" and 
                len(self.current_state["pending_queries"]) > 0)
    
    def clear_job(self):
        """Clears the current job state.""" 
        if os.path.exists(self.state_file):
            os.remove(self.state_file)
        self.__init__(self.state_file)
