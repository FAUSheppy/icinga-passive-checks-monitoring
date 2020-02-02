#!/usr/bin/python3
from   multiprocessing import Process
import subprocess as sp
import socket
import sys
import argparse
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

def executeAndSubmit(user, serviceName, cmd, noSudo):
    if not noSudo:
        dropPivileges(user)

    message = ""
    # run monitoring command
    try:
        subP = sp.run(splitCMD(cmd))
        if subP.returncode != 0:
            raise RuntimeError("Execution of '{}'failed".format(cmd))
        message = "{}\t{}\t{}\t{}\n".format(hostname, serviceName, subP.returncode, subP.stdout)
    except FileNotFoundError:
        print("{} command not found!".format(splitCMD(cmd)[0]),file=sys.stderr)

    # submitt the results
    p = sp.Popen(['/usr/sbin/send_nsca'], stdout=sp.PIPE, stdin=sp.PIPE, stderr=sp.PIPE)
    stdout = p.communicate(input=bytes(message,"utf-8"))
    if p.returncode != 0:
        raise RuntimeError("Execution of send_nsca failed")


def executeAndSubmitAsync(user, serviceName, cmd, noSudo):
    p = Process(target=executeAndSubmit, args=(user,serviceName, cmd, noSudo,))
    p.start()
    return p

def executeConfig(hostname, filename, runAsync, noSudo):
    asyncTasks = []
    # parse config and start tasks
    with open(filename,"r") as f:
        for line in f:
            user, serviceName, cmd = line.split("\t")
            p = executeAndSubmitAsync(user, serviceName, cmd, noSudo)

            # run async or join directly
            if runAsync:
                asyncTasks += [p]
            else:
                p.join()

    # wait for all processes to finish if was async
    for task in asyncTasks:
        task.join()

parser = argparse.ArgumentParser(description='Manage icinga/nsca-ng reports.')
parser.add_argument('-H', '--hostname', help='local identity/hostname)')
parser.add_argument('-c', '--config', dest='configurationFile', default="monitoring.conf", help='Configuration file (default: ./monitoring.conf)')
parser.add_argument('-a', '--async',  dest='async', action="store_const", const=True, default=False, 
                help='Run checks asynchronous')
parser.add_argument('-u', '--ignore-user', dest='ignoreUser', action="store_const", const=True, default=False, 
                help='Run as current user and ignore user column in config file')


if __name__ == '__main__':
    parser = parser.parse_args()
    if not parser.hostname:
        hostname = socket.gethostname()
    else:
        hostname = parser.hostname
    filename = parser.configurationFile
    runAsync = parser.async
    noSudo   = parser.ignoreUser
    executeConfig(hostname, filename, runAsync, noSudo)
