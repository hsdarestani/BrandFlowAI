class AIProvider:
    def generate_text(self,prompt:str,language='en'): raise NotImplementedError
    def generate_json(self,prompt:str,schema:dict|None=None,language='en'): raise NotImplementedError
    def embed_text(self,text:str): return [0.01]*8
    def moderate_content(self,text:str): return {'safe': True, 'risk_score': .08, 'warnings': []}
    def estimate_cost(self,*a,**k): return 0
class MockAIProvider(AIProvider):
    def generate_text(self,prompt,language='en'):
        prefix={'fa':'برای رشد برند','de':'Für nachhaltiges Wachstum','en':'For consistent brand growth'}.get(language,'For growth')
        return f"{prefix}: {prompt[:160]}"
    def generate_json(self,prompt,schema=None,language='en'):
        return {'summary': self.generate_text(prompt,language), 'language': language, 'confidence': .88}
class OpenAICompatibleProvider(MockAIProvider): pass
class AnthropicProvider(MockAIProvider): pass
class GeminiProvider(MockAIProvider): pass
def get_ai_provider(name='mock'): return MockAIProvider()
