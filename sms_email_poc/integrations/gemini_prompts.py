def build_gemini_prompt(context_text: str | None = None) -> str:
    """Return a structured prompt for Gemini to analyze a vehicle diagnostic screen image.

    The prompt asks for a concise JSON with fields: dtcs, pids, likely_causes,
    suggested_tests, confidence_score (0-1).
    """
    base = (
        "You are an expert automotive diagnostic assistant. Analyze the provided "
        "screenshot of a scan tool screen and extract the following in JSON:\n"
        "- dtcs: list of DTC codes (e.g., P0300)\n"
        "- pids: mapping of PID name to value (RPM, STFT, LTFT, MAP, MAF, BATTERY, VOLT)\n"
        "- likely_causes: short list of probable causes with brief reasoning\n"
        "- suggested_tests: ordered steps to verify root cause\n"
        "- confidence_score: number between 0 and 1 indicating reliability of this output\n"
        "Return only valid JSON. If uncertain about values, include null or empty lists.\n"
    )
    if context_text:
        return base + "Context: " + context_text
    return base
