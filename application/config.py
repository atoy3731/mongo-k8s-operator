import os


class Config:
    API_VERSION = os.environ.get('API_VERSION', 'v1alpha1')
    MONGO_IMAGE = os.environ.get('MONGO_IMAGE', 'mongo:4.2')
    REPLICA_SET_NAME = os.environ.get('REPLICA_SET_NAME', 'rs1')