import kopf
from workers.kube_worker import KubeWorker
from workers.mongo_worker import MongoWorker


@kopf.on.create(group='adamtoy.io', version='v1alpha1', plural='mongoclusters')
async def create_mongocluster_handler(event, **kwargs):
    """
    Creates statefulSet and ConfigMap when creating MongoCluster CRD.
    :param event:
    :param kwargs:
    :return:
    """
    kube_worker = KubeWorker()
    kube_worker.create_stateful_set(kwargs['spec']['replicas'], kwargs['namespace'])


@kopf.on.delete(group='adamtoy.io', version='v1alpha1', plural='mongoclusters')
async def delete_mongocluster_hanlder(event, **kwargs):
    """
    Handles clean up and deletion of MongoCluster
    :param event:
    :param kwargs:
    :return:
    """
    kube_worker = KubeWorker()
    kube_worker.delete_stateful_set(kwargs['namespace'])


@kopf.on.field('adamtoy.io', 'v1alpha1', 'mongoclusters', field='spec.replicas')
async def mongocluster_replica_update_handler(old, new, status, namespace, **kwargs):
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


@kopf.on.create(group='', version='v1', plural='pods')
@kopf.on.delete(group='', version='v1', plural='pods')
async def create_delete_pod_hander(event, namespace, **kwargs):
    """
    Handle the deletion of a pod. Checks if it is part of the MongoCluster statefulset, then updates the replicaSet.

    :param event:
    :param kwargs:
    :return:
    """
    if 'app' in kwargs['body']['metadata']['labels'] and kwargs['body']['metadata']['labels']['app'] == 'MongoStatefulSet':
        kube_worker = KubeWorker()
        all_hosts = kube_worker.get_stateful_set_hosts(namespace=namespace)
        mongo_hosts = MongoWorker.get_replset_status(all_hosts)

        MongoWorker.replica_set_reconfig(active_hosts=mongo_hosts['inReplSet'], inactive_hosts=mongo_hosts['outReplSet'])