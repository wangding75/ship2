"""Windows process-scoped resource lease primitive; production broker provisioning required."""
import ctypes, json, msvcrt, os, pathlib, re, time, uuid
from ctypes import wintypes

def fingerprint(pid):
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.restype = wintypes.HANDLE
    handle = kernel.OpenProcess(0x1000, False, int(pid))
    if not handle:
        if ctypes.get_last_error() == 87: return None
        raise PermissionError('Cannot establish process liveness')
    try:
        creation, exit_time, ktime, utime = (wintypes.FILETIME() for _ in range(4))
        code = wintypes.DWORD()
        if not kernel.GetExitCodeProcess(handle, ctypes.byref(code)): raise PermissionError('Cannot query process')
        if code.value != 259: return None
        if not kernel.GetProcessTimes(handle, ctypes.byref(creation), ctypes.byref(exit_time), ctypes.byref(ktime), ctypes.byref(utime)): raise PermissionError('Cannot query creation time')
        return str((creation.dwHighDateTime << 32) | creation.dwLowDateTime)
    finally: kernel.CloseHandle(handle)

class Lease:
    def __init__(self, directory, resources, task, worktree, port, ttl=60):
        self.directory=pathlib.Path(directory); self.resources=sorted(set(resources + ([f'port-{port}'] if port else [])))
        self.task=task; self.worktree=str(pathlib.Path(worktree).resolve()); self.port=port; self.ttl=ttl; self.handles=[]; self.process=None
        self.fence=uuid.uuid4().hex
    def acquire(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        try:
            for resource in self.resources:
                if not re.fullmatch(r'[a-z0-9_-]+', resource): raise ValueError('Invalid resource')
                path=self.directory/(resource+'.lock')
                stream=open(path,'a+b'); stream.seek(0)
                if path.stat().st_size == 0: stream.write(b'0'); stream.flush(); stream.seek(0)
                try: msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
                except OSError: stream.close(); raise RuntimeError('Resource busy: '+resource)
                self.handles.append(stream)
                record=self.directory/(resource+'.json')
                if record.exists():
                    old=json.loads(record.read_text())
                    if old.get('process') and fingerprint(old['process']['pid']) == old['process']['creation']:
                        raise RuntimeError('Prior process still alive; expiration is not release')
            self._save('held')
            return self
        except BaseException: self._unlock(); raise
    def bind(self,pid):
        creation=fingerprint(pid)
        if not creation: raise ValueError('Process not live')
        self.process={'pid':pid,'creation':creation}; self._save('held')
    def _save(self,state):
        for resource in self.resources:
            target=self.directory/(resource+'.json'); temp=target.with_suffix('.'+self.fence+'.tmp')
            temp.write_text(json.dumps(dict(state=state,resource=resource,fence=self.fence,task=self.task,worktree=self.worktree,port=self.port,owner_pid=os.getpid(),process=self.process,expires=time.time()+self.ttl)))
            os.replace(temp,target)
    def release(self):
        if self.process and fingerprint(self.process['pid']) == self.process['creation']: raise RuntimeError('Cannot release live process')
        self.process=None; self._save('released'); self._unlock()
    def _unlock(self):
        for stream in reversed(self.handles):
            stream.seek(0); msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1); stream.close()
        self.handles=[]
