import re
from base64 import b64decode
import urllib.parse

class CookieAnalyzer:
    @staticmethod
    def analyze_cookies(cookies: dict) -> list:
        """
        Analyzes a dictionary of cookies for common manipulation and vulnerabilities
        Returns a list of alerts.
        """
        alerts = []
        
        if not cookies:
            return alerts

        # Dangerous payload signatures
        sqli_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|OR|AND)\b.*\b(FROM|INTO|SET|TABLE|WHERE)\b)",
            r"('.*OR.*')",
            r"(\d=\d)",
            r"('--)"
        ]
        
        xss_patterns = [
            r"(<script.*?>.*?</script>)",
            r"(javascript:)",
            r"(onerror=)",
            r"(onload=)",
            r"(<img.*src=)",
            r"(document\.cookie)"
        ]

        # Compile regexes for speed
        sqli_regexes = [re.compile(p, re.IGNORECASE) for p in sqli_patterns]
        xss_regexes = [re.compile(p, re.IGNORECASE) for p in xss_patterns]

        for key, value in cookies.items():
            try:
                # URL decode value first
                decoded_val = urllib.parse.unquote(str(value))
            except Exception:
                decoded_val = str(value)
                
            # Check length (arbitrarily large cookies are suspicious)
            if len(decoded_val) > 4096:
                alerts.append(f"Cookie '{key}' is abnormally large ({len(decoded_val)} bytes)")

            # Check for Base64 encoded payloads
            if CookieAnalyzer.is_base64(decoded_val):
                try:
                    b64_decoded = b64decode(decoded_val).decode('utf-8', errors='ignore')
                    # Scan the decoded payload
                    if CookieAnalyzer._scan_payload(b64_decoded, sqli_regexes, xss_regexes):
                        alerts.append(f"Cookie '{key}' contains a hidden malicious payload (Base64 encoded)")
                        continue # Already caught
                except Exception:
                    pass

            # Scan the raw/url-decoded payload
            matched_type = CookieAnalyzer._scan_payload(decoded_val, sqli_regexes, xss_regexes)
            if matched_type:
                alerts.append(f"Cookie '{key}' contains suspected {matched_type} payload.")

        return alerts

    @staticmethod
    def _scan_payload(payload: str, sqli_regexes: list, xss_regexes: list) -> str:
        """Returns the type of payload found, or None if safe."""
        for regex in sqli_regexes:
            if regex.search(payload):
                return "SQL Injection"
        for regex in xss_regexes:
            if regex.search(payload):
                return "Cross-Site Scripting (XSS)"
        return None

    @staticmethod
    def is_base64(s: str) -> bool:
        # Basic check for base64 structure. Needs to be a multiple of 4 characters and contain valid alphabet.
        if len(s) % 4 != 0 or len(s) == 0:
            return False
        return bool(re.match(r'^[A-Za-z0-9+/]+={0,2}$', s))
