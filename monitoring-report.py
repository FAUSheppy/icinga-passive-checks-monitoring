#!/usr/bin/python3

import multiprocessing
import subprocess
import socket
import sys
import argparse
import os
import pwd
import grp

import requests

ENCODING = "UTF-8"

def dropPivileges(uid_name, gid_name=None):
    if not gid_name:
        gid_name = "nogroup"

    target_uid = pwd.getpwnam(uid_name).pw_uid
    target_gid = grp.getgrnam(gid_name).gr_gid
    
    os.setgid(target_gid)
    os.setuid(target_uid)

def splitCMD(cmd):
    return list(filter(lambda a: a,cmd.strip("\n").split(" ")))

def executeAndSubmit(hostnameIdent, user, args):

    if not args.no_sudo:
        dropPivileges(user)

    message = ""
    cmd = splitCMD(cmd)

    # run monitoring command
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding=ENCODING)
        message = "{}\t{}\t{}\t{}\n".format(hostnameIdent, serviceName, p.returncode, p.stdout)
    except FileNotFoundError:
        print("{} command not found!".format(splitCMD(cmd)[0]), file=sys.stderr)

    # submitt the results
    if args.gateway:

        if p.returncode == 0:
            status = "OK"
            info   = p.stdout
        else:
            status = "CRITICAL"
            info   = p.stderr

        r = requests.post(args.gateway, json={ "service" : args.hostname,
                "token" : args.token, "status" : status, "info" : info }
        r.raise_for_status()

    else:
        if args.nsca_config:
            nscaCMD = [args.nsca_bin, '-c', args.nsca_config]
        else:
            nscaCMD = [args.nsca_bin]

        nscaProcess = sp.Popen(nscaCMD, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        stdout = nscaProcess.communicate(input=bytes(message, ENCODING))
        if nscaProcess.returncode != 0:
            raise RuntimeError("Execution of send_nsca failed - {}".format(stdout))


def executeAndSubmitAsync(user, service, cmd, sudo):
    p = Process(target=executeAndSubmit, args=(user, service, cmd, no_sudo,))
    p.start()
    return p

def executeConfig(hostnameIdent, args):

    asyncTasks = []

    # parse config and start tasks
    with open(args.filename, "r") as f:

        for line in f:

            # split config #
            user, serviceName, cmd = list(filter(lambda x: x, line.split("\t")))
            p = executeAndSubmitAsync(user, service, cmd, not args.no_sudo)

            # run async or join directly
            if args.async:
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
    parser.add_argument('-a', '--async', action="store_const", const=True, default=False,
                    help='Run checks asynchronous')
    parser.add_argument('-u', '--ignore-user', action="store_const", const=True, default=False, 
                    help='Run as current user and ignore user column in config file')

    parser.add_argument('-x', '--gateway', help='If set, use an async icinga checks gateway')
    parser.add_argument('-t', '--gateway-token', help='Token to use with the gateway')

    args = parser.parse_args()
    if not args.hostname:
        hostname = socket.gethostname()
    else:
        hostname = args.hostname

    executeConfig(hostnameIdent, args)
