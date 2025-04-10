import httpx
from typing import Dict
import os

class SentimentAnalyzer:
    def __init__(self):
        self.api_url = "https://api-inference.huggingface.co/models/cardiffnlp/twitter-roberta-base-sentiment"
        self.headers = {"Authorization": f"Bearer {os.getenv('HF_TOKEN')}"}

    async def analyze(self, text: str) -> Dict:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    headers=self.headers,
                    json={"inputs": text}
                )
                
                if response.status_code != 200:
                    raise Exception("API request failed")
                    
                results = response.json()[0]
                sentiment_scores = {item['label']: item['score'] for item in results}
                dominant = max(results, key=lambda x: x['score'])
                
                return {
                    'scores': sentiment_scores,
                    'dominant': dominant['label'],
                    'confidence': dominant['score']
                }
        except Exception as e:
            print(f"Error in sentiment analysis: {str(e)}")
            return {
                'scores': {'NEUTRAL': 1.0},
                'dominant': 'NEUTRAL',
                'confidence': 1.0
            }
