"""
Risk assessment engine for patient recovery monitoring
"""
from datetime import datetime, timedelta
from app.services.firebase_service import FirebaseService

class RiskEngine:
    """Risk assessment engine"""
    
    def __init__(self):
        self.firebase = FirebaseService()
    
    def calculate_risk_score(self, patient_id: str, current_log: dict, recovery_profile: dict) -> dict:
        """
        Calculate risk score based on current log and recovery profile
        
        Args:
            patient_id: Patient user ID
            current_log: Current daily log data
            recovery_profile: Patient recovery profile
            
        Returns:
            Dictionary with score, status, deviation_flag, and complication_index
        """
        pain_level = current_log.get('pain_level', 0)
        swelling = current_log.get('swelling', False)
        sleep_hours = current_log.get('sleep_hours', 0)
        
        # Get recent logs for trend analysis
        recent_logs = self.firebase.get_recent_patient_logs(patient_id, count=3)
        
        # Initialize risk components
        score = 0
        status = "stable"
        deviation_flag = False
        complication_index = 0
        
        # Rule 1: Pain >= 8 → needs_review
        if pain_level >= 8:
            score += 30
            status = "needs_review"
        
        # Rule 2: Swelling + pain >= 7 → high_risk
        if swelling and pain_level >= 7:
            score += 40
            status = "high_risk"
        
        # Rule 3: Increasing pain trend (3 consecutive days)
        if len(recent_logs) >= 3:
            pain_levels = [log.get('pain_level', 0) for log in recent_logs]
            # Check if pain is increasing (most recent is highest)
            if pain_levels[0] > pain_levels[1] > pain_levels[2]:
                score += 20
                if status == "stable":
                    status = "monitor"
        
        # Rule 4: Deviation from acceptable pain range
        start_date = recovery_profile.get('start_date')
        if start_date:
            if isinstance(start_date, str):
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            elif isinstance(start_date, datetime):
                pass
            else:
                start_date = None
            
            if start_date:
                days_since_start = (datetime.now() - start_date.replace(tzinfo=None)).days
                
                # Determine acceptable pain range based on recovery week
                if days_since_start <= 7:
                    acceptable_max = recovery_profile.get('acceptable_pain_week_1', 5)
                elif days_since_start <= 21:
                    acceptable_max = recovery_profile.get('acceptable_pain_week_3', 4)
                else:
                    acceptable_max = 3
                
                if pain_level > acceptable_max:
                    deviation_flag = True
                    score += 25
                    if status == "stable":
                        status = "monitor"
        
        # Rule 5: Complication Prediction Index
        # If deviation_flag + swelling + sleep < 4 → complication_index = 35%
        if deviation_flag and swelling and sleep_hours < 4:
            complication_index = 35
            score += 15
            if status in ["stable", "monitor"]:
                status = "needs_review"
        
        # Normalize score to 0-100 range
        score = min(score, 100)
        
        # Determine final status if not already set
        if score >= 70:
            status = "high_risk"
        elif score >= 50:
            status = "needs_review"
        elif score >= 30:
            status = "monitor"
        else:
            status = "stable"
        
        return {
            'score': score,
            'status': status,
            'deviation_flag': deviation_flag,
            'complication_index': complication_index
        }
    
    def save_risk_score(self, patient_id: str, risk_data: dict) -> str:
        """
        Save risk score to Firestore
        
        Args:
            patient_id: Patient user ID
            risk_data: Risk score data
            
        Returns:
            Risk score document ID
        """
        risk_data['patient_id'] = patient_id
        risk_data['timestamp'] = datetime.now().isoformat()
        return self.firebase.create_risk_score(risk_data)

