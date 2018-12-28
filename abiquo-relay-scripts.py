#!/usr/bin/env python
# -*- coding: UTF-8 -*-

### LICENSE BSD ###
# Copyright (c) 2011, Salvador Girones, Abiquo
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the Abiquo nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL COPYRIGHT HOLDER BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE
###
#
# This script creates needed scripts in order to configure dhcp server and dhcp relay for Abiquo purpouses:
# http://community.abiquo.com/display/ABI17/Configuring+one+DHCP+Relay+server
#
##

import getopt, sys, os

def create_vlans_script(relay_service_interface, vlan_range, dhcp_server_ip, relay_service_network, relay_server_interface):
   
    minvlan = 0
    maxvlan = 0
    numvlans = 0
    loops = 0
    residual = 0

    try:
        minvlan = int(vlan_range.split('-')[0])
        maxvlan = int(vlan_range.split('-')[1])
        numvlans = maxvlan-minvlan+1
        loops = numvlans / 254
        residual = numvlans % 254
    except:
        print "\nError parsing vlans range.\n"
        sys.exit(2)

    #Generate script for creating vlans and running relay
    try:
        f = open("relay-config", "w")

        data = "#!/bin/bash\n\n"
        
        data += '# Abiquo Dhcp relay config. Vlans generation.\n'
        data += '#\n'
        data += '# chkconfig: 2345 90 60\n'
        data += '# description: Create vlan interfaces and assign ip.\n'
        data += '#               Script generated by Abiquo DHCP Relay script (http://community.abiquo.com/display/ABI17/Configuring+one+DHCP+Relay+server)\n'
        f.write(data)
        
        
        #Create start function
        data = '\nstart() {\n'
        data += '    echo  "Starting subifaces: "\n'

        #Vlans creation
	if loops:
            data += '    for i in `seq 0 %d`; do\n' % (int(loops-1))
            data += '        for j in `seq 1 254`; do\n'
            data += '            vlan=$[$i*254 + $j - 1 + %d]\n' % (int(minvlan))
            data += '            vconfig add %s $vlan\n' % (str(relay_service_interface))
            data += '            ifconfig %s.$vlan up\n' % (str(relay_service_interface))
            data += '            ifconfig %s.$vlan %d.%d.$[$i + %d].$j netmask 255.255.255.255\n' % (str(relay_service_interface), int(relay_service_network.split(".")[0]), int(relay_service_network.split(".")[1]), int(relay_service_network.split(".")[2]))
            data += '        done\n'
            data += '    done\n'

        if residual:
            data += '    for i in `seq 1 %s`; do\n' % (int(residual))
            data += '        vlan=$[%s + $i - 1 + %s]\n' % (int(loops*254), int(minvlan))
            data += '        vconfig add %s $vlan\n' % (str(relay_service_interface))
            data += '        ifconfig %s.$vlan up\n' % (str(relay_service_interface))
            data += '        ifconfig %s.$vlan %d.%d.%d.$i netmask 255.255.255.255\n' % (str(relay_service_interface), int(relay_service_network.split(".")[0]), int(relay_service_network.split(".")[1]), int(relay_service_network.split(".")[2]) + loops)
            data += '    done\n'

        #DHCrelay command
        data += '\n    interfaces="-i %s' % (relay_server_interface)
        if relay_server_interface != relay_service_interface:
            data += ' -i %s "\n' % (relay_service_interface)
        else:
            data += '"\n'
        data += '    for i in `seq %d %d`; do\n' % (minvlan, maxvlan)
        data += '        interfaces="$interfaces -i %s.$i"\n' % (relay_service_interface)
        data += '    done\n'
        data += '    dhcrelay $interfaces %s\n' % (dhcp_server_ip)
        
        #Close start
        data += '}\n'
        f.write(data)

        #Stop
        data = '\nstop() { \n'
        data += '    echo -n $"Stopping $prog: "\n'
        data += '    \n'
        data += '    pkill dhcrelay\n'
        data += '    \n'
        data += '    for i in `seq %d %d`; do\n' % (minvlan, maxvlan)
        data += '        vconfig rem %s.$i\n' % (relay_service_interface)
        data += '    done\n'
        data += '    \n'
        data += '}\n'
        f.write(data)
        
        #Restart
        data = '\nrestart() {\n'
        data += '      stop\n'
        data += '    start\n'
        data += '}\n'
        f.write(data)
        
        # Script logic
        data = '\ncase "$1" in\n'
        data += '  start)\n'
        data += '      start\n'
        data += '    ;;\n'
        data += '  stop)\n'
        data += '      stop\n'
        data += '    ;;\n'
        data += '  restart)\n'
        data += '      restart\n'
        data += '    ;;\n'
        data += '  *)\n'
        data += '    echo $"Usage: $0 {start|stop|restart}"\n'
        data += '    exit 1\n'
        data += 'esac\n'
        f.write(data)
        
        f.close()    
        os.system("chmod +x relay-config")
        

    except Exception, e:
        print "\nError creating relay-config.\n"
        print e
        f.close()
        sys.exit(2)

def usage():
    print "Usage: abiquo-relay-scripts.py [OPTIONS]..."
    print "Creates configuration files and start scripts for the dhcp server and relay.\n"
    print "-h\t--help\t\t\t\t\tThis help screen."
    print "-r\t--relay-server-interface=INTERFACE\tInterface of relay server connected to the management network."
    print "-s\t--relay-service-interface=INTERFACE\tInterface of the relay server connected to service network, where VLANs will be created."
    print "-v\t--vlan-range=VLANRANGE\t\t\tVLAN range (e.g. 2-200)."
    print "-x\t--dhcp-server-ip=IP\t\t\tIP of the DHCP server."
    print "-n\t--relay-service-network=IP\t\tNetwork available for relay service interfaces (has to finish in 0)."
    print ""

def main():
    
    relay_server_interface=None
    relay_service_interface=None
    vlan_range=None
    dhcp_server_ip=None
    relay_service_network=None

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hr:s:v:x:n:b:", ["help", "relay-server-interface=", "relay-service-interface=", "vlan-range=", "dhcp-server-ip=", "relay-service-network="])
    except getopt.GetoptError, err:
        print str(err)
        sys.exit(2)

    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit()
        elif o in ("-r", "--relay-server-interface"):
            relay_server_interface=a
        elif o in ("-s", "--relay-service-interface"):
            relay_service_interface=a
        elif o in ("-v", "--vlan-range"):
            vlan_range=a
        elif o in ("-x", "--dhcp-server-ip"):
            dhcp_server_ip=a
        elif o in ("-n", "--relay-service-network"):
            relay_service_network=a
    
    if not (relay_server_interface and relay_service_interface and vlan_range and dhcp_server_ip and relay_service_network) or relay_service_network.split(".")[3] != "0":
        usage()
        return

    print "-- Generating file --\n"

    #Vlans script
    print " * relay-config\t\tScript to generate VLANs and assign IPs"
    create_vlans_script(relay_service_interface, vlan_range, dhcp_server_ip, relay_service_network, relay_server_interface)
    
    print "\n-- End --\n"


if __name__ == "__main__":
    main()
