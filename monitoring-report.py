#!/usr/bin/python3
from   multiprocessing import Process
import subprocess as sp
import socket
import sys
import argparse
import os
import pwd
import grp

nscaConfig   = ""
sendNscaPath = "/usr/sbin/send_nsca" 

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
    cmd = splitCMD(cmd)
    # run monitoring command
    try:
        subP = sp.run(cmd, stdout=sp.PIPE, stderr=sp.PIPE)
        message = "{}\t{}\t{}\t{}\n".format(hostname, serviceName, subP.returncode,
                                                subP.stdout.decode("utf-8"))
    except FileNotFoundError:
        print("{} command not found!".format(splitCMD(cmd)[0]),file=sys.stderr)

    # submitt the results
    if nscaConfig:
        nscaCMD = [sendNscaPath,'-c', nscaConfig]
    else:
        nscaCMD = [sendNscaPath]
    p = sp.Popen(nscaCMD, stdout=sp.PIPE, stdin=sp.PIPE, stderr=sp.PIPE)
    stdout = p.communicate(input=bytes(message,"utf-8"))
    if p.returncode != 0:
        raise RuntimeError("Execution of send_nsca failed - {}".format(stdout))


def executeAndSubmitAsync(user, serviceName, cmd, noSudo):
    p = Process(target=executeAndSubmit, args=(user,serviceName, cmd, noSudo,))
    p.start()
    return p

def executeConfig(hostname, filename, runAsync, noSudo):
    asyncTasks = []
    # parse config and start tasks
    with open(filename,"r") as f:
        for line in f:
            splitted = list(filter(lambda x: x, line.split("\t")))
            user, serviceName, cmd = splitted
            p = executeAndSubmitAsync(user, serviceName, cmd, noSudo)

            # run async or join directly
            if runAsync:
                asyncTasks += [p]
            else:
                p.join()

    # wait for all processes to finish if was async
    for task in asyncTasks:
        task.join()


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Icinga passive checks and curl report-ins.')
    parser.add_argument('-H', '--hostname', help='Local Identity (often hostname)')
    parser.add_argument('--nsca-config', 
                    help='send-nsca configuration file (default set by nsca-package)')
    parser.add_argument('--nsca-bin', default="/usr/sbin/send_nsca",
                    help='send-nsca executable (default: /usr/sbin/send_nsca)')
    parser.add_argument('-c', '--config', dest='configurationFile', default="monitoring.conf",
                    help='Configuration file (default: ./monitoring.conf)')
    parser.add_argument('-a', '--async',  dest='runAsync', action="store_const", 
                    const=True, default=False, help='Run checks asynchronous')
    parser.add_argument('-u', '--ignore-user', dest='ignoreUser',
                    action="store_const", const=True, default=False, 
                    help='Run as current user and ignore user column in config file')

    parser.add_argument('-x', '--gateway', help='If set, use an async icinga checks gateway')
    parser.add_argument('-t', '--gateway-token', help='Token to use with the gateway')

    args = parser.parse_args()
    if not args.hostname:
        hostname = socket.gethostname()
    else:
        hostname = args.hostname

    nscaConfig   = args.nsca_config
    sendNscaPath = args.nsca_bin
    filename     = args.configurationFile
    noSudo       = args.ignoreUser

    executeConfig(hostname, filename, args.runAsync, noSudo)
