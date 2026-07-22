from django.core.cache import cache

class ResumeProgressTracker:
    """
    Tracks real-time backend processing progress of a resume via Django cache.
    The frontend polls the API endpoint which reads this cache.
    """
    
    CACHE_KEY_TEMPLATE = "resume_analysis_progress:{stored_file_id}"
    CACHE_TIMEOUT = 3600  # 1 hour
    
    # 12 distinct stages that correspond to the UI checklist
    STAGES = [
        "UPLOAD_COMPLETED",
        "PDF_VALIDATED",
        "TEXT_EXTRACTED",
        "RESUME_DETECTED",
        "AI_ANALYSIS_STARTED",
        "SKILLS_ANALYZED",
        "EDUCATION_ANALYZED",
        "EXPERIENCE_ANALYZED",
        "TRUST_ANALYSIS_COMPLETED",
        "MATCH_SCORE_COMPLETED",
        "PROFILE_UPDATED",
        "ANALYSIS_COMPLETED"
    ]

    @classmethod
    def get_key(cls, stored_file_id) -> str:
        return cls.CACHE_KEY_TEMPLATE.format(stored_file_id=stored_file_id)

    @classmethod
    def init_tracker(cls, stored_file_id: int):
        """Initialize the tracker state to UPLOAD_COMPLETED"""
        state = {
            "status": "in_progress",
            "current_stage": "UPLOAD_COMPLETED",
            "completed_stages": ["UPLOAD_COMPLETED"],
            "percentage": 12,
            "error_message": None,
        }
        cache.set(cls.get_key(stored_file_id), state, timeout=cls.CACHE_TIMEOUT)

    @classmethod
    def advance(cls, stored_file_id: int, completed_stage: str):
        """Mark a specific stage as completed and advance the tracker."""
        state = cache.get(cls.get_key(stored_file_id))
        
        # If cache expired or not initialized, fail safely
        if not state:
            return

        if completed_stage not in state["completed_stages"]:
            state["completed_stages"].append(completed_stage)
            
        state["current_stage"] = completed_stage
        
        try:
            # Calculate actual percentage based on completed stages
            pct_per_stage = 100 / len(cls.STAGES)
            pct = int(len(state["completed_stages"]) * pct_per_stage)
            state["percentage"] = min(pct, 100)
        except Exception:
            pass

        if completed_stage == "ANALYSIS_COMPLETED":
            state["status"] = "completed"
            state["percentage"] = 100

        cache.set(cls.get_key(stored_file_id), state, timeout=cls.CACHE_TIMEOUT)

    @classmethod
    def mark_failed(cls, stored_file_id: int, error_message: str):
        """Mark the pipeline as failed and store the error message."""
        state = cache.get(cls.get_key(stored_file_id))
        if not state:
            state = {
                "completed_stages": ["UPLOAD_COMPLETED"],
                "percentage": 12,
            }
            
        state["status"] = "failed"
        state["error_message"] = error_message
        
        cache.set(cls.get_key(stored_file_id), state, timeout=cls.CACHE_TIMEOUT)

    @classmethod
    def get_progress(cls, stored_file_id: int) -> dict:
        """Retrieve the current progress. Default to pending if not found."""
        return cache.get(cls.get_key(stored_file_id)) or {
            "status": "pending",
            "current_stage": None,
            "completed_stages": [],
            "percentage": 0,
            "error_message": None,
        }
