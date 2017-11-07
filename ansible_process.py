#!/usr/bin/evn python
# -*- coding: UTF-8 -*-

import os
import sys
import json
import traceback
import copy

from my_playbook import MyRunner

"""
sources=[{"hostname": "192.168.3.193", "ansible_port":22, "ansible_user":"root", "ansible_ssh_pass":"1234"},
         {"hostname": "192.168.3.199", "ansible_port":22, "ansible_user":"root", "ansible_ssh_pass":"123456"},
         {"hostname": "192.168.3.190", "ansible_port":22, "ansible_user":"root", "ansible_ssh_pass":"1234"}]
runner = MyRunner(sources)
#runner.run('all', 'shell', 'sleep 20')
#runner.run('all', 'copy', 'src=/root/liyunjiang/ansible/sample/god.py dest=/root/')
#runner.run('all', "file", "dest=/root/god.py mode=755 owner=root group=root")
#runner.run('all', "file", "name=/root/tmp_dir state=directory") #make directory
runner.run('all', "file", "name=/root/god.py state=absent") #delete
runner.get_result()
runner.run('all', "service", "name=autofs state=restarted enabled=no")
runner.get_result()

##将主控方/root/a目录推送到指定节点的/tmp目录下
#runner.run('all', "synchronize", "src=/root/a dest=/tmp/ compress=yes")
#runner.get_result()

#在指定节点上执行/root/a.sh脚本(该脚本是在ansible控制节点上的)
runner.run('all', "script", "./test_script.sh")
runner.get_result()
"""

import threading
import multiprocessing
import Queue


class AnsibleProcess(object):
    _queue_recv = None
    _queue_send = None
    _is_running = False

    @staticmethod
    def start(queue_recv, queue_send):
        AnsibleProcess._queue_recv = queue_recv
        AnsibleProcess._queue_send = queue_send

        thred = threading.Thread(target = AnsibleProcess.proc)
        thred.start()
        thred.join()

        print("Exit ansible process.")

    @staticmethod
    def proc():
        while True:
            try:
                #task = AnsibleProcess._queue_recv.get(True, 1)
                task = AnsibleProcess._queue_recv.get(True)
                if not task.has_key('task_id') or not task.has_key('resource') or not task.has_key('mdl_nm') or not task.has_key('mdl_args'):
                    print("Invalid task:%s" % task)
                    continue

                if AnsibleProcess._is_running:
                    print("An Ansible task is running, please wait.")
                    return False

                AnsibleProcess._is_running = True
                try:
                    runner = MyRunner(task['resource'])
                    runner.run('all', task['mdl_nm'], task['mdl_args'])
                    result = runner.get_result()
                    ret_msg = dict()
                    ret_msg['task_id'] = task['task_id']
                    ret_msg['result'] = result
                    AnsibleProcess._queue_send.put(ret_msg)
                except:
                    print("Exception|%s" % traceback.format_exc())
                finally:
                    AnsibleProcess._is_running = False

            except:
                print("Process Ansible task failed.")
                print('Exception|%s' % traceback.format_exc())




class AnsibleApi(object):
    _process = None
    _queue_recv = None
    _queue_send = None
    _stop = False

    _task_id = 0

    _mutex_running = threading.Lock()
    _running_tasks = list()

    _mutex_complete = threading.Lock()
    _complete_tasks = list()

    @staticmethod
    def is_alive():
        if AnsibleApi._process is None or not AnsibleApi._process.is_alive():
            return False
        else:
            return True

    @staticmethod
    def start():
        if AnsibleApi._process is None or not AnsibleApi._process.is_alive():
            try:
                AnsibleApi._queue_recv = multiprocessing.Queue()
                AnsibleApi._queue_send = multiprocessing.Queue()
                AnsibleApi._process = multiprocessing.Process(target = AnsibleProcess.start, args = (AnsibleApi._queue_send, AnsibleApi._queue_recv))
                AnsibleApi._process.start()

                threading.Thread(target = AnsibleApi.fresh_state).start()
                return True
            except:
                print("Start Ansible process failed.")
                print('Exception|%s' % traceback.format_exc())
                return False
        else:
            print("Ansible process is running.")
            return False

    @staticmethod
    def run_task(resource, module_name, module_args):
        if AnsibleApi._process is None or not AnsibleApi._process.is_alive():
            print("Ansible process is stopped.")
            return False

        try:
            task = dict()
            AnsibleApi._task_id += 1
            task['task_id'] = AnsibleApi._task_id
            task['resource'] = resource
            task['mdl_nm'] = module_name
            task['mdl_args'] = module_args

            AnsibleApi._mutex_running.acquire()
            AnsibleApi._running_tasks.append(task)
            AnsibleApi._mutex_running.release()

            AnsibleApi._queue_send.put(task)
        except:
            print('Exception|%s' % traceback.format_exc())
            return False

        return True

    @staticmethod
    def is_task_complete():
        if len(AnsibleApi._running_tasks) > 0:
            return False
        else:
            return True

    @staticmethod
    def stop():
        AnsibleApi._stop = True

        try:
            AnsibleApi._process.terminate()

            AnsibleApi._mutex_running.acquire()
            AnsibleApi._running_tasks = []
            AnsibleApi._mutex_running.release()

            AnsibleApi._mutex_complete.acquire()
            AnsibleApi._complete_tasks = []
            AnsibleApi._mutex_complete.release()
        except:
            print('Exception|%s' % traceback.format_exc())
            return False

        return True

    @staticmethod
    def clear_complete_tasks():
        try:
            AnsibleApi._mutex_complete.acquire()
            AnsibleApi._complete_tasks = []
            AnsibleApi._mutex_complete.release()
        except:
            print('Exception|%s' % traceback.format_exc())
            return False

        return True

    @staticmethod
    def get_result():
        AnsibleApi._mutex_complete.acquire()
        result = copy.deepcopy(AnsibleApi._complete_tasks)
        AnsibleApi._mutex_complete.release()

        return result

    @staticmethod
    def fresh_state():
        while 1:
            if AnsibleApi._stop:
                break

            try:
                ret_msg = AnsibleApi._queue_recv.get(True, 1)
                print("Get return message from Ansible process.")

                compare_task = None
                for task in AnsibleApi._running_tasks:
                    if task['task_id'] == ret_msg['task_id']:
                        compare_task = task

                if compare_task is None:
                    print("Invalid return message from Ansible process.")
                    continue

                AnsibleApi._mutex_running.acquire()
                AnsibleApi._running_tasks.remove(compare_task)
                AnsibleApi._mutex_running.release()

                compare_task['result'] = ret_msg['result']
                AnsibleApi._mutex_complete.acquire()
                AnsibleApi._complete_tasks.append(compare_task)
                AnsibleApi._mutex_complete.release()

            except Queue.Empty:
                pass
            except:
                print('Exception|%s' % traceback.format_exc())

        print("Exit thread fresh_state.")


def main():
    AnsibleApi.start()

    sources=[{"hostname": "192.168.3.193", "ansible_port":22, "ansible_user":"root", "ansible_ssh_pass":"1234"},
             {"hostname": "192.168.3.199", "ansible_port":22, "ansible_user":"root", "ansible_ssh_pass":"123456"},
             {"hostname": "192.168.3.190", "ansible_port":22, "ansible_user":"root", "ansible_ssh_pass":"1234"}]
    AnsibleApi.run_task(sources, 'copy', 'src=/root/liyunjiang/ansible/sample/god.py dest=/root/')

    while True:
        if AnsibleApi.is_task_complete():
            break

    result = AnsibleApi.get_result()
    pretty_dict = json.dumps(result, indent=1)
    print("Ansible Result:%s"%pretty_dict)

    AnsibleApi.clear_complete_tasks()

    AnsibleApi.run_task(sources, "file", "name=/root/god.py state=absent")

    while True:
        if AnsibleApi.is_task_complete():
            break

    result = AnsibleApi.get_result()
    pretty_dict = json.dumps(result, indent=1)
    print("Ansible Result:%s"%pretty_dict)


    AnsibleApi.stop()


if __name__ == '__main__':
    main()