#!/usr/bin/evn python
# -*- coding: UTF-8 -*-

import os
#from ansible.inventory import Inventory
from ansible.inventory.manager import InventoryManager
from ansible.inventory.group import Group
from ansible.inventory.host import Host

#from ansible.vars import VariableManager
from ansible.vars.manager import VariableManager

from ansible.parsing.dataloader import DataLoader
from ansible.executor import playbook_executor
from ansible.utils.display import Display


class MyInventory(InventoryManager):  
    """ 
    this is my ansible inventory object. 
    """  
    def __init__(self, resource, loader, sources=None):
        """ 
        resource的数据格式是一个列表字典，比如 
            { 
                "group1": { 
                    "hosts": [{"hostname": "10.0.0.0", "port": "22", "username": "test", "password": "pass"}, ...], 
                    "vars": {"var1": value1, "var2": value2, ...} 
                } 
            } 
 
        如果你只传入1个列表，这默认该列表内的所有主机属于my_group组,比如 
            [{"hostname": "10.0.0.0", "port": "22", "username": "test", "password": "pass"}, ...] 
        """  
        self.resource = resource
        self.inventory = InventoryManager(loader=loader, sources=sources)
        self.gen_inventory()
  
    def my_add_group(self, hosts, groupname, groupvars=None):
        """ 
        add hosts to a group 
        """
        '''
        my_group = Group(name=groupname)
        print my_group
        self.inventory.add_group(my_group)
        '''
        self.inventory.add_group(groupname)

        # if group variables exists, add them to group  
        if groupvars:
            my_group = self.inventory.get_group(groupname)
            for key, value in groupvars.iteritems():
                my_group.set_variable(key, value)

        # add hosts to group  
        for host in hosts:
            # set connection variables 
            if not host.has_key("hostname"):
                continue

            hostname = host.get("hostname")
            self.inventory.add_host(host=hostname, group=groupname)

            my_host = self.inventory.get_host(hostname)
            # set other variables  
            for key, value in host.iteritems():
                if key not in ["hostname"]:
                    my_host.set_variable(key, value)


    def gen_inventory(self):
        """ 
        add hosts to inventory. 
        """
        if self.resource is None:
            pass
        elif isinstance(self.resource, list):
            #self.my_add_group(self.resource, 'default_group')
            self.my_add_group(self.resource, 'all')
        elif isinstance(self.resource, dict):
            for groupname, hosts_and_vars in self.resource.iteritems():
                self.my_add_group(hosts_and_vars.get("hosts"), groupname, hosts_and_vars.get("vars"))
