#!/usr/bin/env python
#
# Licensed under the Apache License, Version 2.0 (the "License");
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0OA
#
# Authors:
# - Wen Guan, <wen.guan@cern.ch>, 2019

import traceback
try:
    # python 3
    from queue import Queue
except ImportError:
    # Python 2
    from Queue import Queue


from idds.common.constants import (Sections, TransformStatus, TransformType,
                                   CollectionRelationType, CollectionStatus,
                                   ContentStatus, ProcessingStatus)
from idds.common.exceptions import AgentPluginError, IDDSException
from idds.common.utils import setup_logging
from idds.core import (transforms as core_transforms, catalog as core_catalog)
from idds.agents.common.baseagent import BaseAgent

setup_logging(__name__)


class Transformer(BaseAgent):
    """
    Transformer works to process transforms.
    """

    def __init__(self, num_threads=1, poll_time_period=1800, **kwargs):
        super(Transformer, self).__init__(num_threads=num_threads, **kwargs)
        self.config_section = Sections.Transformer
        self.poll_time_period = int(poll_time_period)

        self.new_output_queue = Queue()
        self.monitor_output_queue = Queue()

    def get_new_transforms(self):
        """
        Get new transforms to process
        """

        transform_status = [TransformStatus.Ready]
        transforms_new = core_transforms.get_transforms_by_status(status=transform_status)
        self.logger.info("Main thread get %s New transforms to process" % len(transforms_new))
        return transforms_new

    def generate_transform_output_contents(self, transform, input_collection, output_collection, contents):
        self.logger.debug("generate_transform_output_contents: transform: %s, number of input_contents: %s" % (transform, len(contents)))
        if transform['transform_type'] == TransformType.StageIn:
            if 'stagein_transformer' not in self.plugins:
                raise AgentPluginError('Plugin stagein_transformer is required')
            return self.plugins['stagein_transformer'](transform, input_collection, output_collection, contents)

        return []

    def generate_transform_outputs(self, transform, collections):
        self.logger.debug("Generating transform outputs: transform: %s, collections: %s" % (transform, collections))
        input_collection = None
        output_collection = None
        for collection in collections:
            if collection['relation_type'] == CollectionRelationType.Input:
                input_collection = collection
            if collection['relation_type'] == CollectionRelationType.Output:
                output_collection = collection

        status = [ContentStatus.New, ContentStatus.Failed]
        contents = core_catalog.get_contents_by_coll_id_status(coll_id=input_collection['coll_id'], status=status)
        output_contents = self.generate_transform_output_contents(transform,
                                                                  input_collection,
                                                                  output_collection,
                                                                  contents)

        self.logger.debug("Generating transform number of output contents: %s" % len(output_contents))
        new_processing = None
        if output_contents:
            processing_metadata = {'transform_id': transform['transform_id'],
                                   'input_collection': input_collection['coll_id'],
                                   'output_collection': output_collection['coll_id']}
            new_processing = {'transform_id': transform['transform_id'],
                              'status': ProcessingStatus.New,
                              'processing_metadata': processing_metadata}
            self.logger.debug("Generating transform output processing: %s" % new_processing)

        return {'transform': transform, 'input_collection': input_collection, 'output_collection': output_collection,
                'input_contents': contents, 'output_contents': output_contents, 'processing': new_processing}

    def process_new_transform(self, transform):
        """
        Process new transform
        """
        ret_collections = core_catalog.get_collections_by_request_transform_id(transform_id=transform['transform_id'])
        self.logger.debug("Processing transform(%s): ret_collections: %s" % (transform['transform_id'], ret_collections))

        collections = []
        ret_transform = None
        for request_id in ret_collections:
            for transform_id in ret_collections[request_id]:
                if transform_id == transform['transform_id']:
                    collections = ret_collections[request_id][transform_id]
                    ret_transform = transform
        self.logger.debug("Processing transform(%s): transform: %s, collections: %s" % (transform['transform_id'],
                                                                                        ret_transform,
                                                                                        collections))

        if ret_transform and ret_transform['transform_metadata']['input_collection_changed']:
            return self.generate_transform_outputs(ret_transform, collections)
        else:
            return {}

    def finish_new_transforms(self):
        while not self.new_output_queue.empty():
            try:
                ret = self.new_output_queue.get()
                self.logger.debug("Main thread finishing processing transform: %s" % ret['transform'])
                if ret:
                    core_transforms.add_transform_outputs(transform=ret['transform'],
                                                          input_collection=ret['input_collection'],
                                                          output_collection=ret['output_collection'],
                                                          input_contents=ret['input_contents'],
                                                          output_contents=ret['output_contents'],
                                                          processing=ret['processing'])
            except Exception as ex:
                self.logger.error(ex)
                self.logger.error(traceback.format_exc())

    def get_monitor_transforms(self):
        """
        Get transforms to monitor
        """
        transform_status = [TransformStatus.Transforming]
        transforms = core_transforms.get_transforms_by_status(status=transform_status,
                                                              period=self.poll_time_period)
        self.logger.info("Main thread get %s transforming transforms to process" % len(transforms))
        return transforms

    def process_transform_outputs(transform, collections):
        output_collection = None
        for request_id in collections:
            for transform_id in collections:
                if transform_id == transform['transform_id']:
                    trans_collections = collections[request_id][transform_id]
                    for collection in trans_collections:
                        if collection['relation_type'] == CollectionRelationType.Output:
                            output_collection = collection

        transform_metadata = transform['transform_metadata']
        if not transform_metadata:
            transform_metadata = {}
        transform_metadata['output_collection'] = output_collection['coll_metadata']
        if output_collection['coll_status'] == CollectionStatus.Closed:
            ret = {'transform_id': transform['transform_id'],
                   'status': TransformStatus.Finished,
                   'transform_metadata': transform_metadata}
        elif output_collection['coll_status'] == CollectionStatus.SubClosed:
            ret = {'transform_id': transform['transform_id'],
                   'status': TransformStatus.SubFinished,
                   'transform_metadata': transform_metadata}
        elif output_collection['coll_status'] == CollectionStatus.Failed:
            ret = {'transform_id': transform['transform_id'],
                   'status': TransformStatus.Failed,
                   'transform_metadata': transform_metadata}
        elif output_collection['coll_status'] == CollectionStatus.Deleted:
            ret = {'transform_id': transform['transform_id'],
                   'status': TransformStatus.Deleted,
                   'transform_metadata': transform_metadata}
        else:
            ret = {'transform_id': transform['transform_id'],
                   'status': TransformStatus.Transforming,
                   'transform_metadata': transform_metadata}
        return ret

    def process_monitor_transform(self, transform):
        """
        process monitor transforms
        """
        ret_collections = core_catalog.get_collections_by_request_transform_id(transform_id=transform['transform_id'])
        collections = []
        ret_transform = None
        for request_id in ret_collections:
            for transform_id in ret_collections:
                if transform_id == transform['transform_id']:
                    collections = ret_collections[request_id][transform_id]
                    ret_transform = transform

        if ret_transform and ret_transform['transform_metadata']['input_collection_changed']:
            transform_input = self.generate_transform_outputs(ret_transform, collections)
        if ret_transform and ret_transform['transform_metadata']['output_collection_changed']:
            transform_output = self.process_transform_outputs(ret_transform, collections)
        ret = {'transform_input': transform_input,
               'transform_output': transform_output}
        return ret

    def finish_monitor_transforms(self):
        while not self.monitor_output_queue.empty():
            ret = self.monitor_output_queue.get()
            transform_input = ret['transform_input']
            transform_output = ret['transform_output']
            if transform_input:
                core_transforms.add_transform_output(transform=transform_input['transform'],
                                                     input_collections=transform_input['input_collections'],
                                                     output_collection=transform_input['output_collection'],
                                                     input_contents=transform_input['input_contents'],
                                                     output_contents=transform_input['output_contents'],
                                                     processing=transform_input['processing'])
            if transform_output:
                transform_id = transform_output['transform_id']
                del transform_output['transform_id']
                core_transforms.update_transform(transform_id=transform_id, parameters=transform_output)

    def prepare_finish_tasks(self):
        """
        Prepare tasks and finished tasks
        """
        # finish tasks
        self.finish_new_transforms()
        self.finish_monitor_transforms()

        # prepare tasks
        transforms = self.get_new_transforms()
        for transform in transforms:
            self.submit_task(self.process_new_transform, self.new_output_queue, (transform,))

        transforms = self.get_monitor_transforms()
        for transform in transforms:
            self.submit_task(self.process_monitor_transform, self.monitor_output_queue, (transform,))

    def run(self):
        """
        Main run function.
        """
        try:
            self.logger.info("Starting main thread")

            self.load_plugins()

            for i in range(self.num_threads):
                self.executors.submit(self.run_tasks, i)

            while not self.graceful_stop.is_set():
                try:
                    self.prepare_finish_tasks()
                    self.sleep_for_tasks()
                except IDDSException as error:
                    self.logger.error("Main thread IDDSException: %s" % str(error))
                except Exception as error:
                    self.logger.critical("Main thread exception: %s\n%s" % (str(error), traceback.format_exc()))
        except KeyboardInterrupt:
            self.stop()


if __name__ == '__main__':
    agent = Transformer()
    agent()
