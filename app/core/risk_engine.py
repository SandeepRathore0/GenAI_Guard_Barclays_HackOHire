class RiskEngine:
    @staticmethod
    def calculate_risk_score(threats: list) -> dict:
        """
        Aggregates risk from multiple modules.
        threats: List of dictionaries e.g. [{"source": "email", "score": 85, "severity": "HIGH"}]
        """
        if not threats:
            return {"risk_level": "LOW", "total_score": 0, "details": "No threats detected."}

        total_score = 0
        max_severity = "LOW"
        
        severity_weights = {
            "LOW": 10,
            "MEDIUM": 40,
            "HIGH": 70,
            "CRITICAL": 100
        }

        for threat in threats:
            score = threat.get("score", 0)
            severity = threat.get("severity", "LOW")
            
            total_score += score
            
            if severity_weights.get(severity, 0) > severity_weights.get(max_severity, 0):
                max_severity = severity

        # Normalize score (simple logic for now)
        normalized_score = min(total_score, 100)
        
        return {
            "risk_level": max_severity,
            "total_score": normalized_score,
            "threat_count": len(threats)
        }
