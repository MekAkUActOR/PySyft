
'''
 Things to figure out:
    * create a better test scenario with multiple different stages
    * recursively add subobject in sync_state
    * efficiently check if object was already included in a previous upper level object
    * create state datastructure for better UX
    * check list for each type of object to see if diff must be included or not
'''
from typing import Any, Dict, List, Optional, Type

from syft.service.action.action_data_empty import ActionDataEmpty
from ..types.syft_object import SYFT_OBJECT_VERSION_1, SyftObject
from ..service.code.user_code import UserCode

from ..service.project.project import Project
from ..service.request.request import Request
from ..service.job.job_stash import Job
from ..service.log.log import SyftLog
from ..util.fonts import ITABLES_CSS, fonts_css
from ..util.colors import SURFACE
from ..util import options
from ..service.action.action_object import ActionObject

'''
How to check differences between two objects:
    * by default merge every attr
    * check if there is a custom implementation of the check function
    * check if there are exceptions we do not want to merge
    * check if there are some restrictions on the attr set
'''

only_attr_dict = {
    SyftLog.__name__: ["stdout", "stderr"],
    Job.__name__: ["result", "resolved", "status", "log_id", "parent_job_id",
                   "n_iters", "current_iter", "creation_time", 
                   "updated_at", "user_code_id"],
    UserCode.__name__: ["raw_code", "input_policy_type", "input_policy_init_kwargs",
                        "input_policy_state", 'output_policy_type', 
                        'output_policy_init_kwargs', 'output_policy_state',
                        'parsed_code', 
                        # 'service_func_name', 'unique_func_name', 'input_kwargs',
                        # 'user_unique_func_name', 'code_hash', 'signature',
                        'status', 'submit_time', 'nested_codes', 
                        # enclave_metadata, uses_domain, 'worker_pool_name',
                        ],
    Request.__name__: ["requesting_user_name", 'requesting_user_email',
                       'requesting_user_institution', 'request_time',
                       'updated_at', 'request_hash', 'changes', 'history'
                        ],
    Project.__name__: None,
    ActionObject.__name__: None,
}


class DiffAttr(SyftObject):
    # version
    __canonical_name__ = "DiffAttr"
    __version__ = SYFT_OBJECT_VERSION_1
    attr_name: str
    low_attr: Any
    high_attr: Any
    
    def __repr__(self):
        return f"""{self.attr_name}:
    Low Side value: {self.low_attr}
    High Side value: {self.high_attr}
    """
    
    def __repr_low_side__(self):
        return f'{self.low_attr}'

    def __repr_high_side__(self):
        return f'{self.high_attr}'

except_attrs_dict = {
    SyftLog.__name__: None,
    Job.__name__: None,
    UserCode.__name__: None,
    Request.__name__: None,
    Project.__name__: None,
    ActionObject.__name__: None,
}

class DiffList(DiffAttr):
    # version
    __canonical_name__ = "DiffList"
    __version__ = SYFT_OBJECT_VERSION_1
    diff_ids: List[int] = []
    new_low_ids: List[int] = []
    new_high_ids: List[int] = []

class DiffDict(DiffAttr):
    # version
    __canonical_name__ = "DiffDict"
    __version__ = SYFT_OBJECT_VERSION_1
    diff_keys: List[Any] = []
    new_low_keys: List[Any] = []
    new_high_keys: List[Any] = []

def get_diff_dict(low_dict, high_dict):
    diff_keys = []

    low_dict_keys = set(low_dict.keys())
    high_dict_keys = set(high_dict.keys())
    
    common_keys = low_dict_keys & high_dict_keys
    new_low_keys = low_dict_keys - high_dict_keys
    new_high_keys = high_dict_keys - low_dict_keys
    
    for key in common_keys:
        if low_dict[key] != high_dict[key]:
            diff_keys.append(key)
    
    return diff_keys, list(new_low_keys), list(new_high_keys)
    
def get_diff_list(low_list, high_list):
    diff_ids = []
    new_low_ids = []
    new_high_ids = []
    if len(low_list) != len(high_list):    
        if len(low_list) > len(high_list):
            common_length = len(high_list)
            new_low_ids = list(range(common_length, len(low_list)))
        else:
            common_length = len(low_list)
            new_high_ids = list(range(common_length, len(high_list)))
    else:
        common_length = len(low_list)
    
    for i in range(common_length): 
        if low_list[i] != high_list[i]:
            diff_ids.append(i)
    
    return diff_ids, new_low_ids, new_high_ids

def get_diff_request(low_request, high_request):
    diff_attrs = []
    
    # Sanity check
    if low_request.id != high_request.id:
        raise Exception("Not the same id for low side and high side requests")

    basic_attrs = [
        "requesting_user_name", 
        'requesting_user_email',
        "requesting_user_institution",
        "approving_user_verify_key",
        "request_time",
        "updated_at",
        "request_hash",
    ]
    
    for attr in basic_attrs:
        low_attr = getattr(low_request, attr)
        high_attr = getattr(high_request, attr)
        if low_attr != high_attr:
            diff_attr = DiffAttr(attr_name=attr, low_attr=low_attr, high_attr=high_attr)
            diff_attrs.append(diff_attr)
    
    change_diffs = get_diff_list(low_request.changes, high_request.changes)
    for l in change_diffs:
        if len(l) != 0:
            change_diff = DiffList(
                attr_name="change", 
                low_attr=low_request.changes,
                high_attr=high_request.changes,
                diff_ids=change_diffs[0],
                new_low_ids=change_diffs[1],
                new_high_ids=change_diffs[2]
            )
            diff_attrs.append(change_diff)
            break
    
    history_diffs = get_diff_list(low_request.history, high_request.history)
    for l in history_diffs:
        if len(l) != 0:
            history_diff = DiffList(
                attr_name="history", 
                low_attr=low_request.history,
                high_attr=high_request.history,
                diff_ids=history_diffs[0],
                new_low_ids=history_diffs[1],
                new_high_ids=history_diffs[2]
            )
            diff_attrs.append(history_diff)
            break
       
    return diff_attrs

def get_diff_user_code(low_code, high_code):
    diff_attrs = []

    # Sanity check
    if low_code.id != high_code.id:
        raise Exception("Not the same id for low side and high side requests")

    # Non basic attrs:
    # "nested_codes",
    # "status"

    basic_attrs = [
        "raw_code", 
        "input_policy_type",
        "input_policy_init_kwargs",
        "input_policy_state",
        "output_policy_type",
        "output_policy_init_kwargs",
        "output_policy_state",
        "parsed_code", 
        "service_func_name", 
        "unique_func_name", 
        "user_unique_func_name", 
        "code_hash", 
        "signature",
        "input_kwargs",
        # "enclave_metadata",
        "submit_time",
        "uses_domain",
        "worker_pool_name",
    ]
    
    for attr in basic_attrs:
        low_attr = getattr(low_code, attr)
        high_attr = getattr(high_code, attr)
        if low_attr != high_attr:
            diff_attr = DiffAttr(attr_name=attr, low_attr=low_attr, high_attr=high_attr)
            diff_attrs.append(diff_attr)

    low_status = list(low_code.status.status_dict.values())[0]
    high_status = list(high_code.status.status_dict.values())[0]
    
    if low_status != high_status:
        diff_attr = DiffAttr(attr_name='status', low_attr=low_status, high_attr=high_status)
        diff_attrs.append(diff_attr)

    return diff_attrs

def get_diff_log(low_log, high_log):
    diff_attrs = []

    # Sanity check
    if low_log.id != high_log.id:
        raise Exception("Not the same id for low side and high side requests")

    basic_attrs = [
        "stdout",
        "stderr"
    ]
    
    for attr in basic_attrs:
        low_attr = getattr(low_log, attr)
        high_attr = getattr(high_log, attr)
        if low_attr != high_attr:
            diff_attr = DiffAttr(attr_name=attr, low_attr=low_attr, high_attr=high_attr)
            diff_attrs.append(diff_attr)
    
    return diff_attrs

def get_diff_job(low_job, high_job):
    diff_attrs = []

    # Sanity check
    if low_job.id != high_job.id:
        raise Exception("Not the same id for low side and high side requests")

    # Non basic attrs:
    # "nested_codes",
    # "status"

    basic_attrs = [
        "result", 
        "resolved",
        "status",  
        "log_id", 
        "parent_job_id", 
        "n_iters",
        "current_iter",
        "creation_time",
        "job_pid",
        "job_worker_id",
        "updated_at",
        "user_code_id",
    ]
    
    for attr in basic_attrs:
        low_attr = getattr(low_job, attr)
        high_attr = getattr(high_job, attr)
        if low_attr != high_attr:
            diff_attr = DiffAttr(attr_name=attr, low_attr=low_attr, high_attr=high_attr)
            diff_attrs.append(diff_attr)
    
    return diff_attrs
    
def get_diff_action_object(low_action_object, high_action_object):
    diff_attrs = []

    # Sanity check
    if low_action_object.id != high_action_object.id:
        raise Exception("Not the same id for low side and high side requests")

    # Non basic attrs:
    # "nested_codes",
    # "status"

    basic_attrs = [
        "__attr_searchable__",
        "syft_action_data_cache",
        "syft_blob_storage_entry_id",
        "syft_pointer_type",
        "syft_parent_hashes",
        "syft_parent_op", 
        "syft_parent_args", 
        "syft_parent_kwargs", 
        "syft_history_hash", 
        "syft_internal_type",
        "syft_node_uid", 
        "_syft_pre_hooks__", 
        "_syft_post_hooks__",
        "syft_twin_type", 
        "syft_action_data_type",
        "syft_action_data_repr_",
        "syft_action_data_str_",
        "syft_has_bool_attr",
        "syft_resolve_data",
        "syft_created_at",
        "syft_resolved", 
    ]
    
    for attr in basic_attrs:
        low_attr = getattr(low_action_object, attr)
        high_attr = getattr(high_action_object, attr)
        if low_attr != high_attr:
            diff_attr = DiffAttr(attr_name=attr, low_attr=low_attr, high_attr=high_attr)
            diff_attrs.append(diff_attr)
    
    return diff_attrs
    


func_dict = {#
    SyftLog.__name__: get_diff_log,
    Job.__name__: get_diff_job,
    UserCode.__name__: get_diff_user_code,
    Request.__name__: get_diff_request,
    Project.__name__: None,
    ActionObject.__name__: None,
    # UserCodeStatusChange.__name__: None,
}

def check_diff(low_obj, high_obj, obj_type):
    attrs_to_check = only_attr_dict[obj_type]
    for attr in attrs_to_check:
        low_attr = getattr(low_obj, attr)
        high_attr = getattr(high_obj, attr)

        # if isinstance(low_attr, SyftObject) and isinstance(high_attr, SyftObject)

        if low_attr != high_attr:
            return False

    return True

# check_dict_func = {
#     SyftLogV2.__name__: check_log,
#     Job.__name__: check_job,
#     UserCode.__name__: check_code,
#     Request.__name__: check_request,
#     Project.__name__: check_project
# }
from syft.service.response import SyftError


class SyftString(SyftObject):
    # version
    __canonical_name__ = "SyftString"
    __version__ = SYFT_OBJECT_VERSION_1
    string: str

class Diff(SyftObject): # StateTuple (compare 2 objects)
    # version
    __canonical_name__ = "Diff"
    __version__ = SYFT_OBJECT_VERSION_1
    low_obj: Optional[SyftObject] = None
    high_obj: Optional[SyftObject] = None
    obj_type: Type
    merge_state: str
    diff_list: List[DiffAttr] = []
    
    __repr_attrs__ = [
        # "object_type", 
        "merge_state", 
        "low_state", 
        "high_state"
    ]
    
    @property
    def object_type(self):
        return self.obj_type.__name__
    
    @property
    def low_state(self):
        if self.low_obj is None:
            return 'n/a'
        if self.high_obj is None:
            return 'NEW'
        attr_text = f'{self.object_type}('
        for diff in self.diff_list:
            attr_text += f'{diff.attr_name}={diff.__repr_low_side__()},' + '\n'
        
        if len(self.diff_list) > 0:
            attr_text = attr_text[:-2] + ')'
        else:
            attr_text += ')'
        return attr_text
        # return "DIFF"
    
    @property
    def high_state(self):
        if self.high_obj is None:
            return 'n/a'
        
        if self.low_obj is None:
            return 'NEW'
        attr_text = f'{self.object_type}('
        for diff in self.diff_list:
            attr_text += f'{diff.attr_name}={diff.__repr_high_side__()},' + '\n'
        if len(self.diff_list) > 0:
            attr_text = attr_text[:-2] + ')'
        else:
            attr_text += ')'
        return attr_text
        # return "DIFF"
    
    def get_obj(self):
        if self.merge_state == "NEW":
            return self.low_obj if self.low_obj is not None else self.high_obj
        else:
            return "Error"

    def _repr_html_(self) -> Any:
        if self.low_obj is None and self.high_obj is None:
            return SyftError(message="Something broke")
        
        if self.low_obj is None:
            if hasattr(self.high_obj, '_repr_html_'):
                obj_repr = self.high_obj._repr_html_()
            elif hasattr(self.high_obj, '_inner_repr'):
                obj_repr = self.high_obj._inner_repr()
            else:
                obj_repr = self.__repr__()
            return f"""
    <style>
    {fonts_css}
    .syft-dataset {{color: {SURFACE[options.color_theme]};}}
    .syft-dataset h3,
    .syft-dataset p
        {{font-family: 'Open Sans';}}
        {ITABLES_CSS}
    </style>
    <div class='syft-diff'>
    <h3>{self.object_type} Diff (New {self.object_type}  on the High Side):</h3>
    """ + obj_repr

        
        if self.high_obj is None:
            if hasattr(self.low_obj, '_repr_html_'):
                obj_repr = self.low_obj._repr_html_()
            elif hasattr(self.low_obj, '_inner_repr'):
                obj_repr = self.low_obj._inner_repr()
            else:
                obj_repr = self.__repr__()
            return f"""
    <style>
    {fonts_css}
    .syft-dataset {{color: {SURFACE[options.color_theme]};}}
    .syft-dataset h3,
    .syft-dataset p
        {{font-family: 'Open Sans';}}
        {ITABLES_CSS}
    </style>
    <div class='syft-diff'>
    <h3>{self.object_type} Diff (New {self.object_type}  on the Low Side):</h3>
    """ + obj_repr
    
        if self.merge_state == "SAME":
            attr_text = "No changes between low side and high side"
        else:
            attr_text = ''
            for diff in self.diff_list:
                attr_text += diff.__repr__() + "<br>"
        
            import re
            res = [i.start() for i in re.finditer('\t', attr_text)]

            attr_text = attr_text.replace("\n", "<br>")
            # print("New lines", res)
    
        return f"""
        <style>
        {fonts_css}
        .syft-dataset {{color: {SURFACE[options.color_theme]};}}
        .syft-dataset h3,
        .syft-dataset p
            {{font-family: 'Open Sans';}}
            {ITABLES_CSS}
        </style>
        <div class='syft-diff'>
        <h3>{self.object_type} Diff</h3>
        {attr_text}
        """

def get_type(obj):
    if isinstance(obj, Project):
        return Project
    if isinstance(obj, Request):
        return Request
    if isinstance(obj, UserCode):
        return UserCode
    if isinstance(obj, Job):
        return Job
    if isinstance(obj, SyftLog):
        return SyftLog
    if isinstance(obj, ActionObject):
        return ActionObject
    raise NotImplemented


def get_merge_state(low_obj, high_obj, obj_type):
    if low_obj is None and high_obj is None:
        return "Error"
    if low_obj is None or high_obj is None:
        return "NEW"
    # if check_diff(low_obj, high_obj, obj_type):
    #     return "SAME"
    override_func = func_dict.get(obj_type.__name__, None)
    if override_func:
        diffs = override_func(low_obj, high_obj)
        if len(diffs) == 0:
            return "SAME"
    
    return "DIFF"

class State(SyftObject):
    # version
    __canonical_name__ = "State"
    __version__ = SYFT_OBJECT_VERSION_1
    # diff_to_sync: Dict[str, Diff] = {}
    diff_to_sync: List[Diff] = []
    
    def add_obj(self, low_obj, high_obj):
        if low_obj is None and high_obj is None:
            raise Exception("Both objects are None")
        obj_type = get_type(low_obj if low_obj is not None else high_obj)
        if low_obj is None or high_obj is None:
            diff = Diff(
                low_obj=low_obj,
                high_obj=high_obj,
                obj_type=obj_type,
                merge_state="NEW",
                diff_list=[]
            )
        else:
            obj_type = get_type(low_obj if low_obj is not None else high_obj)
            override_func = func_dict.get(obj_type.__name__, None)
            diff_list = override_func(low_obj, high_obj)
            if len(diff_list) == 0:
                merge_state = "SAME"
            else:
                merge_state = "DIFF"
            # merge_state = get_merge_state(low_obj, high_obj, obj_type.__name__)
            diff = Diff(
                low_obj=low_obj,
                high_obj=high_obj,
                obj_type=obj_type,
                merge_state=merge_state,
                diff_list=diff_list
            )
            # idx = low_obj.id if low_obj is not None else high_obj.id
            # self.diff_to_sync[idx.to_string()] = diff
        self.diff_to_sync.append(diff)

    def objs_to_sync(self):
        objs = []
        for diff in self.diff_to_sync:
            if diff.merge_state == 'NEW':
                objs.append(diff.get_obj())
        return objs


# TODO"
# Split into client.get_sync_state 
# and diff_state = compare_states(low_state, high_state)
def get_sync_state(low_side_client, high_side_client):
    sync_state = State()
    # Projects
    
    dictify = lambda obj_list: {obj.id: obj for obj in obj_list}
    
    low_side_projects = dictify(low_side_client.projects)
    high_side_projects = dictify(high_side_client.projects)
    
    # high_side_projects_ids = [project.id for project in high_side_projects]
    for project in low_side_projects.values():
        if project.id in high_side_projects:
            # check if a changed occured
            # if check_project(project, high_side_projects[project.id]):
            #     projects_to_sync.append(project)
            sync_state.add_obj(project, high_side_projects[project.id])
        else:
            sync_state.add_obj(project, None)
        
    # sync_state["projects"] = projects_to_sync
    # Maybe check for changes on high side as well for projects
    
    # Requests not in Projects
    
    low_side_requests = dictify(low_side_client.requests)
    high_side_requests = dictify(high_side_client.requests)
    
    for request in low_side_requests.values():
        if request.id in high_side_requests:
            # if check_request(request, high_side_requests[request.id]):
            #     requests_to_sync.append(request) 
            sync_state.add_obj(request, high_side_requests[request.id])
        else:
            # requests_to_sync.append(request)
            sync_state.add_obj(request, None)
            
    # sync_state['requests'] = requests_to_sync
    
    # UserCode not in Projects or Requests
    
    low_side_codes = dictify(low_side_client.code)
    high_side_codes = dictify(high_side_client.code)
    
    for code in low_side_codes.values():
        if code.id in high_side_codes:
            # if check_code(code, high_side_codes[code.id]):
            #     user_codes_to_sync.append(code)
            sync_state.add_obj(code, high_side_codes[code.id])
        else:
            # user_codes_to_sync.append(code)
            sync_state.add_obj(code, None)
    # sync_state['codes'] = user_codes_to_sync        
    
    # Jobs
    
    low_side_jobs = dictify(low_side_client.jobs)
    high_side_jobs = dictify(high_side_client.jobs)
    
    for job in high_side_jobs.values():
        if job.id in low_side_jobs:
            # if check_job(low_side_jobs[job.id], job):
            #     jobs_to_sync.append(job)
            sync_state.add_obj(low_side_jobs[job.id], job)
        else:
            # jobs_to_sync.append(job)
            sync_state.add_obj(None, job)
            
        if not isinstance(job.result, ActionDataEmpty):
            sync_state.add_obj(None, job.result)
    # sync_state['jobs'] = jobs_to_sync
    
    # Logs
    low_side_logs = dictify(low_side_client.api.services.log.get_all())
    high_side_logs = dictify(high_side_client.api.services.log.get_all())

    for log in high_side_logs.values():
        if log.id in low_side_logs:
            # if check_job(, log):
            #     logs_to_sync.append(log)
            sync_state.add_obj(low_side_logs[log.id], log)
        else:
            # logs_to_sync.append(log)
            sync_state.add_obj(None, log)
    # sync_state['logs'] = logs_to_sync

    return sync_state

