#!/usr/bin/evn python
# -*- coding: UTF-8 -*-

import os
import json
from datetime import datetime
from ansible.plugins.callback import CallbackBase

class ResultsCollector(CallbackBase):

    def __init__(self, *args, **kwargs):
        super(ResultsCollector, self).__init__(*args, **kwargs)
        self.host_ok = {}
        self.host_unreachable = {}
        self.host_failed = {}

    def v2_runner_on_unreachable(self, result):
        self.host_unreachable[result._host.get_name()] = result
        '''
        print "~~~~~~~~~~~~~~~~~~"
        #pretty_dict = json.dumps(total_info)
        print "host:", result._host.get_name()
        pretty_dict = json.dumps(result._result, indent=1)
        print "unreachable:", pretty_dict
        print "~~~~~~~~~~~~~~~~~~\n"
        '''

    def v2_runner_on_ok(self, result,  *args, **kwargs):
        self.host_ok[result._host.get_name()] = result
        '''
        print "VVVVVVVVVVVVVVVVVV"
        print "host:", result._host.get_name()
        #pretty_dict = json.dumps(total_info)
        pretty_dict = json.dumps(result._result, indent=1)
        print "success:", pretty_dict
        print "VVVVVVVVVVVVVVVVVV\n"
        '''

    def v2_runner_on_failed(self, result,  *args, **kwargs):
        self.host_failed[result._host.get_name()] = result
        '''
        print "XXXXXXXXXXXXXXXXXX"
        print "host:", result._host.get_name()
        #pretty_dict = json.dumps(total_info)
        pretty_dict = json.dumps(result._result, indent=1)
        print "failed:", pretty_dict
        print "XXXXXXXXXXXXXXXXXX\n"
        '''
