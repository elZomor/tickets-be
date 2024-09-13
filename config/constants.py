import environ

env = environ.Env()

FE_URL = env.str("FE_URL", default="http://localhost:8000")