import json, os, pathlib, subprocess, sys, tempfile, unittest
from lease import Lease

class LeaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
    def make(self, resource='unity_editor', port=7800, ttl=60): return Lease(self.tmp.name,[resource],'T03',os.getcwd(),port,ttl)
    def test_process_competition_and_return(self):
        lease=self.make().acquire()
        code="from lease import Lease; import sys; Lease(sys.argv[1],['unity_editor'],'other','.',7800).acquire()"
        child=subprocess.run([sys.executable,'-c',code,self.tmp.name],cwd=pathlib.Path(__file__).parent,capture_output=True)
        self.assertNotEqual(child.returncode,0); self.assertIn(b'Resource busy',child.stderr)
        lease.release(); other=self.make().acquire(); other.release()
    def test_port_collision(self):
        first=self.make().acquire()
        try:
            with self.assertRaises(RuntimeError): self.make('gpu_capture').acquire()
        finally: first.release()
    def test_expiry_cannot_release_live_process(self):
        lease=self.make(ttl=-1).acquire(); lease.bind(os.getpid())
        with self.assertRaises(RuntimeError): lease.release()
        lease._unlock() # simulate broker crash; persistent process record must prevent takeover
        with self.assertRaises(RuntimeError): self.make().acquire()
        for p in pathlib.Path(self.tmp.name).glob('*.json'): p.unlink()
    def test_dead_child_release(self):
        lease=self.make().acquire()
        child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(1)'])
        try: lease.bind(child.pid); child.wait(); lease.release()
        finally:
            if child.poll() is None: child.kill(); child.wait()
    def test_path_injection(self):
        with self.assertRaises(ValueError): self.make('../escape',None).acquire()

if __name__=='__main__': unittest.main(verbosity=2)
