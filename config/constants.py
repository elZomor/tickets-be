import environ

env = environ.Env()

FE_URL = env.str("FE_URL", default="http://localhost:8000")
CLERK_SIGNING_SECRET = env.str("CLERK_SIGNING_SECRET", default="")
DEV_TOKEN = env.str("DEV_TOKEN", default='')
GOOGLE_CLIENT_ID = env.str('GOOGLE_CLIENT_ID', default='')
GOOGLE_CLIENT_SECRET = env.str('GOOGLE_CLIENT_SECRET', default='')
