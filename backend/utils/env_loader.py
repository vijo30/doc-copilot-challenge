import os
from dotenv import load_dotenv

def load_env():
    """
    Load environment variables from the project root .env file.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    env_path = os.path.join(base_dir, '.env')
    
    if os.path.exists(env_path):
        load_dotenv(env_path)
    else:
        print(f"Warning: .env file not found at {env_path}")