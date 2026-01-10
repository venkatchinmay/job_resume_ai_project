import os
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from functools import lru_cache

class JinjaTemplate:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(JinjaTemplate, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Assuming prompts are one level up from prompt_loader, then in a prompts folder? 
        # Previous code: prompts_dir = os.path.join(os.path.dirname(current_dir), "prompts")
        # prompt_loader is inside job_resume_ai_project. 
        # So current_dir is config/../prompt_loader. 
        # dirname(current_dir) is job_resume_ai_project.
        # So prompts is job_resume_ai_project/prompts. Correct.
        prompts_dir = os.path.join(os.path.dirname(current_dir), "prompts")
        
        self._file_loader = FileSystemLoader(prompts_dir)
        self.env = Environment(loader=self._file_loader)
        self._initialized = True

    #@lru_cache(maxsize=128)
    def _get_template(self, template_name): 
        try:
            print("Loading Template name: ", template_name)
            return self.env.get_template(template_name)
        except TemplateNotFound:
            raise ValueError(f"Template {template_name} not found")

    def load_prompt(self, template_name, arguments: dict = None):
        if arguments is None:
            arguments = {}
        template = self._get_template(template_name)
        return template.render(**arguments)