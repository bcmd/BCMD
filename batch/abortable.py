# quasi-replacement for subprocess.call that runs the call in a thread with a timeout
# at present, only the args actually used in model_bcmd are supported

import subprocess
import threading

def call(args, stdout, stderr, timeout):
    scope = {}
    def target():
        scope['proc'] = subprocess.Popen(args, stdout=stdout, stderr=stderr)
        scope['proc'].wait()
    
    thread = threading.Thread(target=target)
    thread.start()
    
    thread.join(timeout)
    if thread.is_alive():
        print 'timeout exceeded, killing simulation'
        scope['proc'].terminate()
        thread.join()
        return False
    
    return True
