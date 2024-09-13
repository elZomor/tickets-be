import environ

env = environ.Env()

FE_URL = env.str("FE_URL", default="http://localhost:8000")
CLERK_SIGNING_SECRET = env.str("CLERK_SIGNING_SECRET", default="")
