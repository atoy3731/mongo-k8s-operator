from pymongo import MongoClient
from pymongo.errors import OperationFailure
from config import Config


class MongoWorker:
    @staticmethod
    def _get_current_repl_set_conf(mongo_uri):
        """
        Get the current ReplicaSet configuration from Mongo.
        :param mongo_uri: URI of the Mongo cluster
        :return: Object containing replicaSet configuration.
        """
        c = MongoClient(mongo_uri, replicaSet=Config.REPLICA_SET_NAME)
        db = c.local
        return db.system.replset.find_one()

    @staticmethod
    def get_replset_status(hosts):
        """
        Scan the existing Mongo replicaSet to see which nodes and and are not a part of it.
        :param hosts: List of hosts matching StatefulSet selector.
        :return: Object containing hosts in and out of replica set.
        """
        replSetHosts = {
            'inReplSet': [],
            'outReplSet': []
        }

        for host in hosts:
            c = MongoClient('mongodb://{0}:27017'.format(host))

            try:
                c.admin.command("replSetGetStatus")
                replSetHosts['inReplSet'].append(host)
            except OperationFailure as E:
                if E.code == 94:
                    replSetHosts['outReplSet'].append(host)

        return replSetHosts

    @staticmethod
    def replica_set_initialize(hosts):
        """
        Initialization of a replicaSet (if it does not already exist).
        :param hosts: List of hosts to initialize replicaSet.
        :return: N/A
        """
        replica_set_config = {
            '_id': Config.REPLICA_SET_NAME,
            'members': []
        }

        for i, host in enumerate(hosts):
            replica_set_config['members'].append({
                '_id': i,
                'host': '{0}:27017'.format(host)
            })

        c = MongoClient('mongodb://{0}:27017'.format(hosts[0]))
        c.admin.command("replSetInitiate", replica_set_config)

    @staticmethod
    def replica_set_reconfig(active_hosts, inactive_hosts):
        """
        Reconfigure the replicaSet to add inactive hosts
        :param active_hosts: Array of hostnames currently active in the Mongo ReplicaSet
        :param inactive_hosts: Array of hostnames currently inactive in the Mongo Replicaset
        :return:
        """
        replica_set_config = {
            '_id': Config.REPLICA_SET_NAME,
            'members': []
        }

        mongo_uri = 'mongodb://'

        node_count = 0

        for host in active_hosts:
            mongo_uri += '{0}:27017,'.format(host)
            replica_set_config['members'].append({
                '_id': node_count,
                'host': '{0}:27017'.format(host)
            })
            node_count += 1

        mongo_uri = mongo_uri[:-1]

        for host in inactive_hosts:
            replica_set_config['members'].append({
                '_id': node_count,
                'host': '{0}:27017'.format(host)
            })
            node_count += 1

        current_rs_conf = MongoWorker._get_current_repl_set_conf(mongo_uri)
        replica_set_config['version'] = current_rs_conf['version'] + 1
        replica_set_config['protocolVersion'] = current_rs_conf['protocolVersion']

        c = MongoClient(mongo_uri, replicaSet=Config.REPLICA_SET_NAME)
        c.admin.command({'replSetReconfig': replica_set_config})