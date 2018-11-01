#!/usr/bin/python3
import subprocess as sp
from multiprocessing import Process
import sys
import os
import pwd
import grp

def dropPivileges(uid_name, gid_name=None):
    if not gid_name:
        gid_name = "nogroup"

    target_uid = pwd.getpwnam(uid_name).pw_uid
    target_gid = grp.getgrnam(gid_name).gr_gid
    
    os.setgid(target_gid)
    os.setuid(target_uid)

def splitCMD(cmd):
    return list(filter(lambda a: a,cmd.strip("\n").split(" ")))

def executeAndSubmit(user, serviceName, cmd):
    dropPivileges(user)
    message = ""
    # run monitoring command
    try:
        subP = sp.run(splitCMD(cmd))
        message = "{}\t{}\t{}\t{}\n".format(hostname, serviceName, subP.returncode, subP.stdout)
    except FileNotFoundError:
        print("{} command not found!".format(splitCMD(cmd)[0]),file=sys.stderr)

    # submitt the results
    p = sp.Popen(['/usr/sbin/send_nsca'], stdout=sp.PIPE, stdin=sp.PIPE, stderr=sp.PIPE)
    stdout = p.communicate(input=bytes(message,"utf-8"))

def executeAndSubmitAsync(user, serviceName, cmd):
    p = Process(target=executeAndSubmit, args=(user,serviceName, cmd,))
    p.start()
    return p

def executeConfig(hostname, filename):
    asyncTasks = []
    # parse config and start tasks
    with open(filename,"r") as f:
        for line in f:
            user, serviceName, cmd = line.split("\t")
            p = executeAndSubmitAsync(user, serviceName, cmd)
            asyncTasks += [p]

    # wait for all processes to finish
    for task in asyncTasks:
        task.join()

if __name__ == '__main__':
    hostname = "atlantishq.de"
    filename = "monitoring.conf"
    executeConfig(hostname, filename)
