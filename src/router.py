import logging
import re
from typing import Literal, Dict, Any, Optional
from pydantic import BaseModel, Field
import litellm

log = logging.getLogger(__name__)

IntentType = Literal[
    "room_timetable",
    "course_timetable",
    "lecturer_timetable",
    "lecturer_info",
    "mensa_menu",
    "mensa_details",
    "campus_map",
    "university_calendar",
    "conflict_analysis",
    "smalltalk_fallback",
]

class RouteStrategy(BaseModel):
    action: Literal["direct_tool", "agent_flow", "ask_clarification"]
    reason: str

class RouterOutput(BaseModel):
    intent: IntentType
    confidence: float = Field(ge=0.0, le=1.0)
    entities: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extrahierte Entitäten wie Raum (z.B. 'M-102'), Datum, Kurs-ID",
    )
    strategy: RouteStrategy


class Router:
    def __init__(self):
        # Einfache Heuristiken für den deterministischen Fast-Path
        self.heuristics = [
            (r"(?i)\b[A-Z]{1,2}-\d{3}\b", "room_timetable", "direct_tool"),
            (r"(?i)\b(mensa|speiseplan|essen|hunger)\b", "mensa_menu", "agent_flow"),
            (r"(?i)\b(allergene|zusatzstoffe|vegan|vegetarisch)\b", "mensa_details", "agent_flow"),
            (r"(?i)\b(wo ist|lageplan|gebäude|raum finden)\b", "campus_map", "agent_flow"),
            (r"(?i)\b(semesterzeiten|vorlesungsfreie zeit|prüfungszeit)\b", "university_calendar", "direct_tool"),
        ]

    def _fast_path(self, text: str) -> Optional[RouterOutput]:
        """Stufe 1: Deterministische Klassifikation mittels RegEx/Keywords."""
        for pattern, intent, action in self.heuristics:
            if re.search(pattern, text):
                return RouterOutput(
                    intent=intent, # type: ignore
                    confidence=1.0,
                    entities={},
                    strategy=RouteStrategy(
                        action=action, # type: ignore
                        reason=f"Regex Match: {pattern}"
                    )
                )
        return None

    async def _llm_fallback(self, text: str) -> RouterOutput:
        """Stufe 2: LLM-basierte Klassifikation (Fallback)."""
        prompt = f"""
Du bist ein präziser Intent-Router für das Raumzeit-Buchungssystem der Hochschule Karlsruhe. 
Analysiere die Nachricht und ordne sie einem Intent zu.

Verfügbare Intents:
- room_timetable: Fragen nach der Belegung eines konkreten Raums.
- course_timetable: Fragen nach dem Stundenplan eines Studiengangs.
- lecturer_timetable: Fragen nach dem Stundenplan eines Dozenten.
- lecturer_info: Fragen nach E-Mail oder Sprechzeiten eines Dozenten.
- mensa_menu: Fragen nach dem allgemeinen Speiseplan der Mensa.
- mensa_details: Fragen nach Allergenen, Preisen oder Zusatzstoffen für ein bestimmtes Gericht/Linie.
- campus_map: Fragen nach dem Weg, Lageplänen oder Gebäuden.
- university_calendar: Fragen nach Semesterzeiten, Prüfungsphasen oder Ferien.
- conflict_analysis: Fragen nach Überschneidungen im Stundenplan.
- smalltalk_fallback: Für Smalltalk oder falls nichts anderes passt.

Gib nur ein JSON-Objekt im angegebenen Schema zurück.

Nachricht: "{text}"
"""
        # Wir nutzen ein kleines, schnelles Modell für das Routing (z.B. GPT-4o-mini oder gemini-1.5-flash)
        # Hier als Fallback verwenden wir das vom User konfigurierte Modell. Da der Router aber unabhängig vom Hauptagenten
        # agieren soll, importieren wir die config.
        from src.config import settings
        
        # Für den Router bevorzugen wir ein schnelles Modell, wenn möglich. 
        if settings.llm_model:
            model = settings.llm_model
        else:
            from src.agent import _DEFAULTS
            model = _DEFAULTS.get(settings.llm_provider, "gemini/gemini-2.5-flash")
        
        # API Keys setzen
        import os
        if "claude" in model: os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key
        elif "gemini" in model: os.environ["GEMINI_API_KEY"] = settings.gemini_api_key
        elif "groq" in model: os.environ["GROQ_API_KEY"] = settings.groq_api_key
        elif "mistral" in model: os.environ["MISTRAL_API_KEY"] = settings.mistral_api_key
        elif "openrouter" in model: os.environ["OPENROUTER_API_KEY"] = settings.openrouter_api_key

        try:
            response = await litellm.acompletion(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                response_format=RouterOutput, # Nutze Pydantic Modell für Structured Output
                max_tokens=512,
            )
            raw = response.choices[0].message.content
            if raw:
                return RouterOutput.model_validate_json(raw)
        except Exception as e:
            log.warning("LLM Routing fehlgeschlagen: %s", e)
            
        # Fallback im Fallback
        return RouterOutput(
            intent="smalltalk_fallback",
            confidence=0.0,
            entities={},
            strategy=RouteStrategy(
                action="agent_flow",
                reason="LLM fallback failed, defaulting to smalltalk/fallback"
            )
        )

    async def classify_message(self, text: str, user_context: dict, state: dict) -> RouterOutput:
        """Hauptmethode für das Routing einer Nachricht."""
        
        # State prüfen (pending_intent?)
        # pending_intent = state.get("pending_intent")
        # TODO: Logik für pending_intent implementieren, sobald DB erweitert ist
        
        # 1. Fast Path
        result = self._fast_path(text)
        if result:
            log.debug("Router Fast-Path Hit: %s", result.intent)
            return result

        # 2. LLM Fallback
        log.debug("Router LLM-Fallback für: %.50s...", text)
        return await self._llm_fallback(text)

router_instance = Router()
