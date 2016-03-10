import json
import logging
import collections

from common.interface.transfer import TransferInterface
from common.interface.deletion import DeletionInterface
from common.interface.siteinfo import SiteInfoSourceInterface
from common.interface.replicainfo import ReplicaInfoSourceInterface
from common.interface.webservice import RESTService
from common.dataformat import Dataset, Block, Site, Group, DatasetReplica, BlockReplica
from common.misc import unicode2str
import common.configuration as config

logger = logging.getLogger(__name__)

class PhEDExInterface(TransferInterface, DeletionInterface, SiteInfoSourceInterface, ReplicaInfoSourceInterface):
    """
    Interface to PhEDEx using datasvc REST API.
    """

    ProtoBlockReplica = collections.namedtuple('ProtoBlockReplica', ['block_name', 'group_name', 'is_custodial', 'time_created', 'time_updated'])

    def __init__(self):
        self._interface = RESTService(config.phedex.url_base)

        self._last_request_time = 0
        self._last_request_url = ''

        # Due to the way PhEDEx is set up, we are required to see block replica information
        # when fetching the list of datasets. Might as well cache it.
        # Cache organized as {site: {ds_name: [protoblocks]}}
        self._block_replicas = {}

    def get_site_list(self, filt = '*'): #override (SiteInfoSourceInterface)
        options = []
        if type(filt) is str and len(filt) != 0:
            options = ['node=' + filt]
        elif type(filt) is list:
            options = ['node=%s' % s for s in filt]

        source = self._make_request('nodes', options)

        site_list = []

        for entry in source:
            site_list.append(Site(entry['name'], host = entry['se'], storage_type = Site.storage_type(entry['kind']), backend = entry['technology']))

        return site_list

    def get_group_list(self, filt = '*'): #override (SiteInfoSourceInterface)
        options = []
        if type(filt) is str and len(filt) != 0:
            options = ['group=' + filt]
        elif type(filt) is list:
            options = ['group=%s' % s for s in filt]

        source = self._make_request('groups', options)

        group_list = []
        
        for entry in source:
            group_list.append(Group(entry['name']))

        return group_list

    def get_datasets_on_site(self, site, filt = '/*/*/*'): #override (ReplicaInfoSourceInterface)
        options = []
        if type(filt) is str and len(filt) != 0:
            options = ['dataset=' + filt]
        elif type(filt) is list:
            options = ['dataset=%s' % s for s in filt]

        self._block_replicas[site] = {}

        ds_name_list = []

        source = self._make_request('blockreplicas', ['subscribed=y', 'show_dataset=y', 'node=' + site.name] + options)

        logger.info('Got %d dataset info from site %s', len(source), site)

        for dataset_entry in source:
            ds_name = dataset_entry['name']
            
            ds_name_list.append(ds_name)

            self._block_replicas[site][ds_name] = []

            for block_entry in dataset_entry['block']:
                replica_entry = block_entry['replica'][0]

                protoreplica = PhEDExInterface.ProtoBlockReplica(
                    block_name = block_entry['name'].replace(ds_name + '#', ''),
                    group_name = replica_entry['group'],
                    is_custodial = (replica_entry['custodial'] == 'y'),
                    time_created = replica_entry['time_create'],
                    time_updated = replica_entry['time_update']
                )

                self._block_replicas[site][ds_name].append(protoreplica)

        return ds_name_list
        
    def make_replica_links(self, dataset, sites, groups): #override (ReplicaInfoSourceInterface)
        # sites argument not used because cache is already site-aware
        logger.info('Making replica links for dataset %s', dataset.name)

        custodial_sites = []
        num_blocks = {}

        for site, ds_block_list in self._block_replicas.items():
            if dataset.name not in ds_block_list:
                continue

            for protoreplica in ds_block_list[dataset.name]:
                try:
                    block = next(b for b in dataset.blocks if b.name == protoreplica.block_name)
                except StopIteration:
                    logger.warning('Replica interface found a block %s that is unknown to dataset %s', protoreplica.block_name, dataset.name)
                    continue

                if protoreplica.group_name is not None:
                    try:
                        group = groups[protoreplica.group_name]
                    except KeyError:
                        logger.warning('Group %s for replica of block %s not registered.', protoreplica.group_name, block.name)
                        continue
                else:
                    group = None
                
                replica = BlockReplica(block, site, group = group, is_custodial = protoreplica.is_custodial, time_created = protoreplica.time_created, time_updated = protoreplica.time_updated)

                block.replicas.append(replica)

                if protoreplica.is_custodial and site not in custodial_sites:
                    custodial_sites.append(site)

                try:
                    num_blocks[site] += 1
                except KeyError:
                    num_blocks[site] = 1

        for site, num in num_blocks.items():
            replica = DatasetReplica(dataset, site, is_partial = (num != len(dataset.blocks)), is_custodial = (site in custodial_sites))

            dataset.replicas.append(replica)
            
    def _make_request(self, resource, options = []):
        """
        Make a single PhEDEx request call. Returns a list of dictionaries from the body of the query result.
        """

        resp = self._interface.make_request(resource, options)
        logger.info('PhEDEx returned a response of ' + str(len(resp)) + ' bytes.')

        result = json.loads(resp)['phedex']
        unicode2str(result)

        logger.debug(result)

        self._last_request = result['request_timestamp']
        self._last_request_url = result['request_url']

        for metadata in ['request_timestamp', 'instance', 'request_url', 'request_version', 'request_call', 'call_time', 'request_date']:
            result.pop(metadata)
        
        # the only one item left in the results should be the result body
        return result.values()[0]


if __name__ == '__main__':

    from argparse import ArgumentParser

    parser = ArgumentParser(description = 'PhEDEx interface')

    parser.add_argument('command', metavar = 'COMMAND', help = 'Command to execute.')
    parser.add_argument('options', metavar = 'EXPR', nargs = '+', default = [], help = 'Option string as passed to PhEDEx datasvc.')

    args = parser.parse_args()

    logger.setLevel(logging.DEBUG)
    
    command = args.command

    interface = PhEDExInterface()

    print interface._make_request(command, args.options)
