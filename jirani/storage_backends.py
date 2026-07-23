# storage_backends.py

# from storages.backends.s3boto3 import S3Boto3Storage


# class StaticStorage(S3Boto3Storage):
#     location = "static"
#     default_acl = "public-read"
#     file_overwrite = False
#     object_parameters = {
#         "CacheControl": "max-age=86400",
#     }


# class MediaStorage(S3Boto3Storage):
#     location = "media"
#     file_overwrite = False
#     default_acl = "public-read"