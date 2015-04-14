#!/bin/sh

# This script initiates a shutdown when the power putton has been
# pressed. Loosely based on the sample that ships with the acpid package.
# If the acpid sample is present as a real config file (as it was in earlier
# versions of acpid), we skip this script. (Purging and reinstalling acpid
# resolves this situation, or simply deleting /etc/acpi/events/powerbtn.)

if [ -f /etc/acpi/events/powerbtn -o -f /etc/acpi/events/powerbtn.dpkg-bak ] ; then 
	logger Acpi-support not handling power button, acpid handler exists at /etc/acpi/events/powerbtn or /etc/acpi/events/powerbtn.dpkg-bak.
	exit 0
fi

[ -e /usr/share/acpi-support/policy-funcs ] || exit 0

. /usr/share/acpi-support/policy-funcs

if CheckPolicy; then
	exit 0
fi

if [ -x /etc/acpi/powerbtn.sh ] ; then
	# Compatibility with old config script from acpid package
	/etc/acpi/powerbtn.sh
elif [ -x /etc/acpi/powerbtn.sh.dpkg-bak ] ; then
        # Compatibility with old config script from acpid package
	# which is still around because it was changed by the admin
        /etc/acpi/powerbtn.sh.dpkg-bak
else
	# Safe handling.
	PROBE=`config-pin -q P8.26`
	v=`echo $PROBE | cut -c $((${#PROBE}))`
        [ $? -eq 0 ] && [ "$v" = "0" ] && exit 0
	/sbin/shutdown -h -P now "Power button pressed"
fi

