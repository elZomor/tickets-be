from django.core.files.storage import FileSystemStorage

# Custom local storage backend
local_storage = FileSystemStorage(location='local_files/', base_url='/local_files/')
