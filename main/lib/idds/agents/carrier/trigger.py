#!/usr/bin/env python
#
# Licensed under the Apache License, Version 2.0 (the "License");
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0OA
#
# Authors:
# - Wen Guan, <wen.guan@cern.ch>, 2019 - 2022

import traceback

from idds.common import exceptions
from idds.common.constants import ProcessingStatus, ProcessingLocking
from idds.common.utils import setup_logging, truncate_string
from idds.core import processings as core_processings
from idds.agents.common.eventbus.event import (EventType,
                                               TriggerProcessingEvent,
                                               TerminatedProcessingEvent,
                                               SyncProcessingEvent)

from .utils import handle_trigger_processing, is_process_terminated
from .poller import Poller

setup_logging(__name__)


class Trigger(Poller):
    """
    Trigger works to trigger to release jobs
    """

    def __init__(self, num_threads=1, poll_period=10, retries=3, retrieve_bulk_size=2,
                 name='Trigger', message_bulk_size=1000, **kwargs):
        super(Trigger, self).__init__(num_threads=num_threads, name=name, **kwargs)

        if hasattr(self, 'trigger_max_number_workers'):
            self.max_number_workers = int(self.trigger_max_number_workers)

    def get_trigger_processings(self):
        """
        Get trigger processing
        """
        try:
            if not self.is_ok_to_run_more_processings():
                return []
            self.show_queue_size()

            processing_status = [ProcessingStatus.ToTrigger, ProcessingStatus.Triggering]
            processings = core_processings.get_processings_by_status(status=processing_status,
                                                                     locking=True, update_poll=True,
                                                                     not_lock=True,
                                                                     only_return_id=True,
                                                                     bulk_size=self.retrieve_bulk_size)
            if processings:
                self.logger.info("Main thread get [ToTrigger, Triggering] processings to process: %s" % (str(processings)))

            for pr_id in processings:
                self.logger.info("UpdateProcessingEvent(processing_id: %s)" % pr_id)
                event = TriggerProcessingEvent(publisher_id=self.id, processing_id=pr_id)
                self.event_bus.send(event)

            return processings
        except exceptions.DatabaseException as ex:
            if 'ORA-00060' in str(ex):
                self.logger.warn("(cx_Oracle.DatabaseError) ORA-00060: deadlock detected while waiting for resource")
            else:
                # raise ex
                self.logger.error(ex)
                self.logger.error(traceback.format_exc())
        return []

    def handle_trigger_processing(self, processing):
        try:
            log_prefix = self.get_log_prefix(processing)
            process_status, update_contents, ret_msgs, parameters = handle_trigger_processing(processing,
                                                                                              self.agent_attributes,
                                                                                              logger=self.logger,
                                                                                              log_prefix=log_prefix)

            new_process_status = process_status
            if is_process_terminated(process_status):
                new_process_status = ProcessingStatus.Terminating

            update_processing = {'processing_id': processing['processing_id'],
                                 'parameters': {'status': new_process_status,
                                                'substatus': process_status,
                                                'locking': ProcessingLocking.Idle}}

            if parameters:
                # special parameters such as 'output_metadata'
                for p in parameters:
                    update_processing['parameters'][p] = parameters[p]

            ret = {'update_processing': update_processing,
                   'update_contents': update_contents,
                   'messages': ret_msgs,
                   'processing_status': new_process_status}
        except exceptions.ProcessFormatNotSupported as ex:
            self.logger.error(ex)
            self.logger.error(traceback.format_exc())

            retries = processing['update_retries'] + 1
            if not processing['max_update_retries'] or retries < processing['max_update_retries']:
                proc_status = ProcessingStatus.Running
            else:
                proc_status = ProcessingStatus.Failed
            error = {'update_err': {'msg': truncate_string('%s' % (ex), length=200)}}

            # increase poll period
            update_poll_period = int(processing['update_poll_period'].total_seconds() * self.poll_period_increase_rate)
            if update_poll_period > self.max_update_poll_period:
                update_poll_period = self.max_update_poll_period

            update_processing = {'processing_id': processing['processing_id'],
                                 'parameters': {'status': proc_status,
                                                'locking': ProcessingLocking.Idle,
                                                'update_retries': retries,
                                                'update_poll_period': update_poll_period,
                                                'errors': processing['errors'] if processing['errors'] else {}}}
            update_processing['parameters']['errors'].update(error)

            ret = {'update_processing': update_processing,
                   'update_contents': []}
        except Exception as ex:
            self.logger.error(ex)
            self.logger.error(traceback.format_exc())

            retries = processing['update_retries'] + 1
            if not processing['max_update_retries'] or retries < processing['max_update_retries']:
                proc_status = ProcessingStatus.Running
            else:
                proc_status = ProcessingStatus.Failed
            error = {'update_err': {'msg': truncate_string('%s' % (ex), length=200)}}
            update_processing = {'processing_id': processing['processing_id'],
                                 'parameters': {'status': proc_status,
                                                'locking': ProcessingLocking.Idle,
                                                'update_retries': retries,
                                                'errors': processing['errors'] if processing['errors'] else {}}}
            update_processing['parameters']['errors'].update(error)
            update_processing['parameters'] = self.load_poll_period(processing, update_processing['parameters'])

            ret = {'update_processing': update_processing,
                   'update_contents': []}
        return ret

    def process_trigger_processing(self, event):
        self.number_workers += 1
        try:
            if event:
                # pr_status = [ProcessingStatus.New]
                self.logger.info("process_trigger_processing, event: %s" % str(event))
                pr = self.get_processing(processing_id=event._processing_id, status=None, locking=True)
                if not pr:
                    self.logger.error("Cannot find processing for event: %s" % str(event))
                else:
                    log_pre = self.get_log_prefix(pr)
                    self.logger.info(log_pre + "process_trigger_processing")
                    ret = self.handle_trigger_processing(pr)
                    # self.logger.info(log_pre + "process_trigger_processing result: %s" % str(ret))

                    self.update_processing(ret, pr)

                    if (('processing_status' in ret and ret['processing_status'] == ProcessingStatus.Terminating)
                        or (event._content and 'Terminated' in event._content and event._content['Terminated'])):   # noqa W503
                        self.logger.info(log_pre + "TerminatedProcessingEvent(processing_id: %s)" % pr['processing_id'])
                        event = TerminatedProcessingEvent(publisher_id=self.id, processing_id=pr['processing_id'], content=event._content)
                        self.event_bus.send(event)
                    else:
                        if ((event._content and 'has_updates' in event._content and event._content['has_updates'])
                            or ('update_contents' in ret and ret['update_contents'])    # noqa W503
                            or ('new_contents' in ret and ret['new_contents'])          # noqa W503
                            or ('messages' in ret and ret['messages'])):                # noqa E129
                            self.logger.info(log_pre + "SyncProcessingEvent(processing_id: %s)" % pr['processing_id'])
                            event = SyncProcessingEvent(publisher_id=self.id, processing_id=pr['processing_id'])
                            self.event_bus.send(event)
        except Exception as ex:
            self.logger.error(ex)
            self.logger.error(traceback.format_exc())
        self.number_workers -= 1

    def init_event_function_map(self):
        self.event_func_map = {
            EventType.TriggerProcessing: {
                'pre_check': self.is_ok_to_run_more_processings,
                'exec_func': self.process_trigger_processing
            }
        }

    def run(self):
        """
        Main run function.
        """
        try:
            self.logger.info("Starting main thread")

            self.load_plugins()
            self.init()

            self.add_default_tasks()

            self.init_event_function_map()

            task = self.create_task(task_func=self.get_trigger_processings, task_output_queue=None, task_args=tuple(), task_kwargs={}, delay_time=60, priority=1)
            self.add_task(task)

            self.execute()
        except KeyboardInterrupt:
            self.stop()


if __name__ == '__main__':
    agent = Trigger()
    agent()
