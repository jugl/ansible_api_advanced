#!/usr/bin/evn python
# -*- coding: UTF-8 -*-

import os
import sys
import json
from collections import namedtuple
from ansible.parsing.dataloader import DataLoader
from ansible.vars.manager import VariableManager
#from ansible.inventory.manager import InventoryManager
from ansible.playbook.play import Play
from ansible.executor.task_queue_manager import TaskQueueManager
#from ansible.plugins.callback import CallbackBase

from ansible.executor.playbook_executor import PlaybookExecutor

from my_callback import ResultsCollector
from my_inventory import MyInventory

from ansible.plugins.callback import CallbackBase
class ResultCallback(CallbackBase):
    """A sample callback plugin used for performing an action as results come in

    If you want to collect all results into a single object for processing at
    the end of the execution, look into utilizing the ``json`` callback plugin
    or writing your own custom callback plugin
    """
    def v2_runner_on_ok(self, result, **kwargs):
        """Print a json representation of the result

        This method could store the result in an instance attribute for retrieval later
        """
        host = result._host
        print(json.dumps({host.name: result._result}, indent=4))

class MyRunner(object):  
    """ 
    This is a General object for parallel execute modules. 
    """  
    def __init__(self, resource=None, sources=None, *args, **kwargs):  
        self.resource = resource
        self.sources = sources
        self.inventory = None
        self.variable_manager = None  
        self.loader = None  
        self.options = None  
        self.passwords = None  
        self.callback = None  
        self.__initializeData()  
        self.results_raw = {}  
  
    def __initializeData(self):
        """ 
        初始化ansible 
        """

        Options = namedtuple('Options', ['connection','module_path', 'forks', 'timeout',  'remote_user',  
                'ask_pass', 'private_key_file', 'ssh_common_args', 'ssh_extra_args', 'sftp_extra_args',  
                'scp_extra_args', 'become', 'become_method', 'become_user', 'ask_value_pass', 'verbosity',  
                'check', 'listhosts', 'listtasks', 'listtags', 'syntax', 'diff'])
        self.options = Options(connection='smart', module_path='/usr/share/ansible', forks=100, timeout=10,  
                remote_user='root', ask_pass=False, private_key_file=None, ssh_common_args=None, ssh_extra_args=None,  
                sftp_extra_args=None, scp_extra_args=None, become=None, become_method=None,  
                become_user='root', ask_value_pass=False, verbosity=None, check=False, listhosts=False,  
                listtasks=False, listtags=False, syntax=False, diff=False)

        #Options = namedtuple('Options', ['connection', 'module_path', 'forks', 'become', 'become_method', 'become_user', 'check', 'diff'])
        #self.options = Options(connection='local', module_path='/path/to/mymodules', forks=100, become=None, become_method=None, become_user=None, check=False, diff=False)

        # initialize needed objects
        self.loader = DataLoader()

        #self.passwords = dict(sshpass=None, becomepass=None)
        self.passwords = dict(vault_pass='secret')

        self.inventory = MyInventory(self.resource, self.loader, self.sources).inventory

        self.variable_manager = VariableManager(loader=self.loader, inventory=self.inventory)
  
    def run(self, hosts, module_name, module_args):
        """ 
        run module from andible ad-hoc. 
        module_name: ansible module_name 
        module_args: ansible module args 
        """  
        # create play with tasks  
        play_source = dict(  
                name="Ansible Play",
                hosts=hosts,
                gather_facts='no',
                #tasks = [dict(action=dict(module='shell', args='ls'), register='shell_out'),
                #    dict(action=dict(module='debug', args=dict(msg='{{shell_out.stdout}}')))]
                tasks=[dict(action=dict(module=module_name, args=module_args))]
            )
        play = Play().load(play_source, variable_manager=self.variable_manager, loader=self.loader)
  
        # actually run it  
        tqm = None  
        self.callback = ResultsCollector()
        #self.callback = ResultCallback()
        try:  
            tqm = TaskQueueManager(  
                    inventory=self.inventory,
                    variable_manager=self.variable_manager,
                    loader=self.loader,
                    options=self.options,
                    passwords=self.passwords,
                    )
            tqm._stdout_callback = self.callback
            result = tqm.run(play)
        finally:
            if tqm is not None:
                tqm.cleanup()
  
    #def run_playbook(self, host_list, role_name, role_uuid, template_dir=None, temp_param=None):
    def run_playbook(self, play_book):
        """ 
        run ansible palybook 
        """  
        try:  
            self.callback = ResultsCollector()
            filenames = [play_book]    #playbook的路径  
            print('ymal file path:%s'% filenames)

            '''
            if not os.path.exists(template_dir):  #模板文件的路径  
                print('%s is not exsit'%template_dir)
                sys.exit()
  
            extra_vars = {}     #额外的参数 sudoers.yml以及模板中的参数，它对应ansible-playbook test.yml --extra-vars "host='aa' name='cc' "  
            host_list_str = ','.join([item for item in host_list])  
            extra_vars['host_list'] = host_list_str  
            extra_vars['username'] = role_name  
            extra_vars['template_dir'] = template_dir  
            extra_vars['command_list'] = temp_param.get('cmdList')  
            extra_vars['role_uuid'] = 'role-%s'%role_uuid  
            self.variable_manager.extra_vars = extra_vars  
            print('playbook: extra_vars%s'%self.variable_manager.extra_vars)
            '''
            # actually run it  
            executor = PlaybookExecutor(playbooks=filenames,
                                        inventory=self.inventory,
                                        variable_manager=self.variable_manager,
                                        loader=self.loader,
                                        options=self.options,
                                        passwords=self.passwords,
                                        )
            executor._tqm._stdout_callback = self.callback
            executor.run()
        except Exception as e:
            print("run_playbook:%s"%e)

    def get_result(self):
        result_show = {'success':{}, 'failed':{}, 'unreachable':{}}
        self.results_raw = {'success':[], 'failed':[], 'unreachable':[]}
        for host, result in self.callback.host_ok.items():
            self.results_raw['success'].append(host)
            result_show['success'][host] = result._result

        for host, result in self.callback.host_failed.items():
            self.results_raw['failed'].append(host)
            result_show['failed'][host] = result._result['msg']

        for host, result in self.callback.host_unreachable.items():
            self.results_raw['unreachable'].append(host)
            result_show['unreachable'][host]= result._result['msg']

        #pretty_dict = json.dumps(result_show, indent=1)
        #print("Ansible Result:%s"%pretty_dict)

        return self.results_raw
