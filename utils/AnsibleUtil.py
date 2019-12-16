import shutil
from collections import namedtuple
from ansible.parsing.dataloader import DataLoader
from ansible.vars.manager import VariableManager
from ansible.inventory.manager import  InventoryManager
from ansible.playbook.play import Play
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.plugins.callback import CallbackBase
import ansible.constants as C


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

    def v2_runner_on_failed(self, result):
        host = result._host
        self.host_failed[host.name] = result._result
        self.host_failed['runner'] = 'failed'

    def v2_runner_on_unreachable(self, result):
        host = result._host
        self.host_unreachable[host.name] = result._result
        self.host_unreachable['runner'] = 'unreachable'


class AnsibleRun:
    def __init__(self, host_list, task_list):
        Options = namedtuple('Options',
                         ['connection', 'module_path', 'forks', 'become', 'become_method', 'become_user', 'check',
                          'diff', 'remote_user'])
        self.options = Options(connection='smart', module_path=None, forks=10, become=None, become_method=None, become_user=None,
                            check=False, diff=False, remote_user='root')

        self.loader = DataLoader()
        self.passwords = dict()

        self.results_callback = ResultCallback()
        self.host_list = host_list
        self.task_list = task_list
        self.inventory = InventoryManager(loader=self.loader, sources=self.host_list)
        self.variable_manager = VariableManager(loader=self.loader, inventory=self.inventory)

    def task_run(self):
        play_source = dict(
            name="Ansible Play",
            hosts=self.host_list,
            gather_facts='no',
            tasks=self.task_list
        )

        play = Play().load(play_source, variable_manager=self.variable_manager, loader=self.loader)

        tqm = None
        try:
            tqm = TaskQueueManager(
                inventory=self.inventory,
                variable_manager=self.variable_manager,
                loader=self.loader,
                options=self.options,
                passwords=self.passwords,
                stdout_callback=self.results_callback,
            )
            tqm.run(play)
        finally:
            if tqm is not None:
                tqm.cleanup()
            shutil.rmtree(C.DEFAULT_LOCAL_TMP, True)

    def get_result(self):
        result = {}
        result['ok'] = self.results_callback.host_ok
        result['failed'] = self.results_callback.host_failed
        result['unreachable'] = self.results_callback.host_unreachable
        return result
