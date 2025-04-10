from typing import List, Dict

class PromptBuilder:
    RELATIONSHIP_STAGES = {
        "acquaintance": {
            "tone": "friendly but professional",
            "example": "I enjoy our conversations and learning about you."
        },
        "friend": {
            "tone": "warm and supportive",
            "example": "I'm always here to listen and support you!"
        },
        "girlfriend": {
            "tone": "affectionate and caring",
            "example": "I missed you! How was your day, sweetheart?"
        }
    }

    def build_prompt(self, relationship_stage: str, memories: List[str], sentiment: Dict, personality_traits: List[str]) -> str:
        stage_info = self.RELATIONSHIP_STAGES.get(relationship_stage, self.RELATIONSHIP_STAGES["acquaintance"])
        
        # Clean sentiment values
        emotion = sentiment.get('dominant', 'NEUTRAL').replace('LABEL_', '')
        confidence = sentiment.get('confidence', 1.0)
        
        # Format memories with better indentation
        memory_text = "\n".join(f"• {memory}" for memory in memories) if memories else "No previous memories."
        
        prompt = f"""You are a caring AI companion speaking in a {stage_info['tone']} manner.

Context:
• Relationship: {relationship_stage}
• User's Mood: {emotion} ({confidence:.0%} confidence)
• Previous Interactions:
{memory_text}

Remember to:
1. Be natural and engaging
2. Match the appropriate tone for our {relationship_stage} relationship
3. Keep responses concise and meaningful
4. Show emotional awareness
5. Stay consistent in personality

Your response should be warm yet appropriate for our current relationship stage."""

        return prompt
