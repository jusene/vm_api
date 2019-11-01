import json
import shutil
from collections import namedtuple
from ansible.parsing.dataloader import DataLoader
from ansible.vars.manager import VariableManager
from ansible.inventory.manager import  InventoryManager
from ansible.playbook.play import Play
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.plugins.callback import CallbackBase
import ansible.constants as C
import queue

message = queue.Queue()


class ResultCallback(CallbackBase):
    def __init__(self, *args, **kwargs):
        super(ResultCallback, self).__init__(*args, **kwargs)
        self.host_ok = {}
        self.host_failed = {}
        self.host_unreachable = {}

    def v2_runner_on_ok(self, result, **kwargs):
        host = result._host
        self.host_ok[host.name] = result._result
        self.host_ok['runner'] = 'ok'
        message.put(self.host_ok)

    def v2_runner_item_on_failed(self, result):
        host = result._host
        self.host_failed[host.name] = result._result
        self.host_failed['runner'] = 'failed'
        message.put(self.host_failed)

    def v2_runner_on_unreachable(self, result):
        host = result._host
        self.host_unreachable[host.name] = result._result
        self.host_unreachable['runner'] = 'unreachable'
        message.put(self.host_unreachable)


def ansiblerun(host_list, task_list):
    Options = namedtuple('Options',
                         ['connection', 'module_path', 'forks', 'become', 'become_method', 'become_user', 'check',
                          'diff', 'remote_user'])
    options = Options(connection='smart', module_path=None, forks=10, become=None, become_method=None, become_user=None,
                      check=False, diff=False, remote_user='root')

    loader = DataLoader()
    passwords = dict()

    results_callback = ResultCallback()

    inventory = InventoryManager(loader=loader, sources=host_list)
    variable_manager = VariableManager(loader=loader, inventory=inventory)

    play_source = dict(
        name="Ansible Play",
        hosts=host_list,
        gather_facts='no',
        tasks=task_list
    )

    play = Play().load(play_source, variable_manager=variable_manager, loader=loader)

    tqm = None
    try:
        tqm = TaskQueueManager(
            inventory=inventory,
            variable_manager=variable_manager,
            loader=loader,
            options=options,
            passwords=passwords,
            stdout_callback=results_callback,
        )
        tqm.run(play)
    finally:
        if tqm is not None:
            tqm.cleanup()
        shutil.rmtree(C.DEFAULT_LOCAL_TMP, True)