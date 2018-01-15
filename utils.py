# -*- coding: utf-8 -*-
from __future__ import print_function # Python 2/3 compatibility
import subprocess
import os
import logging

import ferkee_props as fp

#
# Run a generic command through the shell
#
def run_command(command, toSend=None):
    # print ("Running command: %s" % command)
    p = subprocess.Popen(command,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, shell=True)
    return p.communicate(toSend)[0]

#
# Send an email alert
# 
def send_alert(to, subject, alert):
    alert = alert.replace("'", "")
    if fp.props['noEmail']:
        return None
    sendEmailOutput = run_command ("sendEmail -f '%s' -t %s -u '%s' -s smtp.gmail.com:587 -xu '%s' -xp '%s' -m '%s'" % (fp.props['from'], to, subject, fp.props['from'], fp.props['from_p'], alert))
    print ("sendEmail Result: %s" % sendEmailOutput)

