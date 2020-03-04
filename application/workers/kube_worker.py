from kubernetes import client, config
from kubernetes.client.rest import ApiException

from config import Config
import os


class KubeWorker:
    def __init__(self):
        """
        Load Kubernetes cluster configuration situational (in or out of cluster) and create APIs
        to interface with it.
        """
        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()

        # Set up Kubernetes clients
        self.apps_v1_api = client.AppsV1Api()
        self.core_v1_api = client.CoreV1Api()

    def delete_stateful_set(self, namespace=None):
        """
        Delete and clean up stateful set and configmap after CRD instantiation deletion.
        :param namespace: Namespace of resource to delete.
        :return: N/A
        """
        self.apps_v1_api.delete_namespaced_stateful_set(
            name='mongo',
            namespace=namespace
        )

        self.core_v1_api.delete_namespaced_config_map(
            name='mongo-configmap',
            namespace=namespace
        )

    def create_stateful_set(self, replicas=3, volumeSize=10, namespace=None):
        """
        Create the StatefulSet for the Mongo cluster within a namespace.
        :param replicas: Number of replicas for the StatefulSet.
        :params volumeSize: The size of the volume to be generated via PVC and attached to pods
                            within the statefulSet.
        :param namespace: Namespace to deploy to.
        :return: N/A
        """
        self._create_mongo_configmap(namespace=namespace)

        stateful_set = client.V1beta1StatefulSet(
            metadata=client.V1ObjectMeta(
                name='mongo',
                namespace=namespace,
                labels={
                    "app": "MongoStatefulSet"
                }
            ),
            status=client.V1beta1StatefulSetStatus(
                replicas=replicas
            ),
            spec=client.V1beta1StatefulSetSpec(
                volume_claim_templates=[
                  client.V1PersistentVolumeClaim(
                      spec=client.V1PersistentVolumeClaimSpec(
                          access_modes=['ReadWriteOnce'],
                          resources=client.V1ResourceRequirements(
                              requests={
                                  "storage": '{0}Gi'.format(volumeSize)
                              }
                          )
                      )
                  )
                ],
                replicas=replicas,
                selector=client.V1LabelSelector(
                    match_labels={
                        "app": "MongoStatefulSet"
                    }
                ),
                service_name="mongo-service",
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(
                        name='mongo-pod',
                        namespace=namespace,
                        labels={
                            "app": "MongoStatefulSet"
                        }
                    ),
                    spec=client.V1PodSpec(
                        containers=[
                            client.V1Container(
                                name='mongo-container',
                                image=Config.MONGO_IMAGE,
                                image_pull_policy='Always',
                                ports=[
                                    client.V1ContainerPort(
                                        name='mongo',
                                        container_port=27017,
                                        protocol='TCP'
                                    )
                                ],
                                volume_mounts=[
                                    client.V1VolumeMount(
                                        name='mongo-config-volume',
                                        mount_path='/etc/mongo'
                                    )
                                ],
                                command=[
                                    "mongod",
                                    "-f",
                                    "/etc/mongo/mongod.conf"
                                ]
                            )
                        ],
                        volumes=[
                            client.V1Volume(
                                name='mongo-config-volume',
                                config_map=client.V1ConfigMapVolumeSource(default_mode=0o555, name='mongo-configmap')
                            )
                        ]
                    )
                )
            )
        )

        try:
            self.apps_v1_api.create_namespaced_stateful_set(
                namespace=namespace,
                body=stateful_set
            )
        except ApiException as E:
            if E.status == 409:
                print('Stateful Set already exists.')
            else:
                raise E

    def _create_mongo_configmap(self, namespace):
        """
        Create the Mongo ConfigMap that contains the 'mongod.conf' file for ReplicaSet configuration.
        :param namespace: Namespace to deploy configmap to.
        :return: N/A
        """
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'templates', 'mongod.conf'), 'r') as file:
            mongo_config_map = client.V1ConfigMap(
                metadata=client.V1ObjectMeta(
                    name='mongo-configmap'
                ),
                data={
                    "mongod.conf": file.read()
                }
            )

            try:
                self.core_v1_api.create_namespaced_config_map(
                    namespace=namespace,
                    body=mongo_config_map
                )
            except ApiException as E:
                if E.status == 409:
                    print('Config Map already exists.')
                else:
                    raise E

    def get_stateful_set_hosts(self, namespace):
        """
        Get the active list of hosts of the StatefulSet pods.
        :param namespace: Namespace of deployment.
        :return: N/A
        """
        active_pod_hosts = []

        stateful_pods = self.core_v1_api.list_namespaced_pod(
            namespace=namespace,
            label_selector='app=MongoStatefulSet'
        )

        for pod in stateful_pods.items:
            if pod.status.phase == 'Running':
                active_pod_hosts.append(pod.metadata.name)

        return active_pod_hosts

    def alter_replicas(self, replicas, namespace):
        """
        Alter the number of replicas in the Mongo StatefulSet.
        :param replicas: New number of replicas.
        :param namespace: Namespace of the StatefulSet.
        :return: N/A
        """
        self.apps_v1_api.patch_namespaced_stateful_set_scale(
            name='mongo',
            namespace=namespace,
            body={
                'replicas': replicas
            }
        )
