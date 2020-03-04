import kopf
from workers.kube_worker import KubeWorker
from workers.mongo_worker import MongoWorker


@kopf.on.create(group='adamtoy.io', version='v1alpha1', plural='mongoclusters')
def create_mongocluster_handler(event, **kwargs):
    """

    :param event:
    :param kwargs:
    :return:
    """
    kube_worker = KubeWorker()
    kube_worker.create_stateful_set(kwargs['spec']['replicas'], kwargs['namespace'])


@kopf.on.field('adamtoy.io', 'v1alpha1', 'mongoclusters', field='spec.replicas')
def mongocluster_replica_update_handler(old, new, status, namespace, **kwargs):
    """
    Updates replicas for StatefulSet. If removing a replica, also removes it from Mongo ReplicaSet.
    :param old: Old mongocluster object (used as a basis of comparison).
    :param new: New MongoCluster object.
    :param status:
    :param namespace: Namespace of the existing Mongo cluster.
    :param kwargs:
    :return:
    """
    kube_worker = KubeWorker()
    kube_worker.alter_replicas(new)


@kopf.on.delete(group='', version='v1', plural='pods')
async def delete_pod_hander(event, name, **kwargs):
    """

    :param event:
    :param kwargs:
    :return:
    """
    print('event: {}'.format(event))
    print('kwargs: {}'.format(kwargs))


@kopf.on.field(group='', version='v1', plural='pods', field='status.phase')
def update_pod_handler(old, new, status, namespace, **kwargs):
    """
    Handle the deletion of a pod. Checks if it is part of the MongoCluster statefulset.
    :param event:
    :param kwargs:
    :return:
    """
