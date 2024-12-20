import environ

env = environ.Env()

FE_URL = env.str("FE_URL", default="http://localhost:8000")
CLERK_SIGNING_SECRET = env.str("CLERK_SIGNING_SECRET", default="")
DEV_TOKEN = env.str("DEV_TOKEN", default='')
GOOGLE_CLIENT_ID = env.str('GOOGLE_CLIENT_ID', default='')
GOOGLE_CLIENT_SECRET = env.str('GOOGLE_CLIENT_SECRET', default='')
AWS_ACCESS_KEY_ID = env.str('AWS_ACCESS_KEY_ID', default='')
AWS_SECRET_ACCESS_KEY = env.str('AWS_SECRET_ACCESS_KEY', default='')
AWS_STORAGE_BUCKET_NAME = env.str('AWS_STORAGE_BUCKET_NAME', default='')
AWS_S3_SIGNATURE_NAME = env.str('AWS_S3_SIGNATURE_NAME', default='')
AWS_S3_REGION_NAME = env.str('AWS_S3_REGION_NAME', default='')
ACCESS_TOKEN_LIFETIME = env.int('ACCESS_TOKEN_LIFETIME', default=5)
REFRESH_TOKEN_LIFETIME = env.int('REFRESH_TOKEN_LIFETIME', default=30)
