#####################################################################################
# Copyright 2011 Normation SAS
#####################################################################################
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, Version 3.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#####################################################################################

.DEFAULT_GOAL := localdepends

RUDDER_VERSION_TO_PACKAGE = <put Rudder version or version-snapshot here>
VIRTUALENV_RELEASE = 12.0.7
WGET := $(if $(PROXY), http_proxy=$(PROXY) ftp_proxy=$(PROXY)) /usr/bin/wget -q

localdepends: ./rudder-sources ./relay-api/virtualenv/virtualenv.py ./relay-api/virtualenv-1.10.1/virtualenv.py

./rudder-sources.tar.bz2:
	$(WGET) -O rudder-sources.tar.bz2 http://www.rudder-project.org/archives/rudder-sources-${RUDDER_VERSION_TO_PACKAGE}.tar.bz2

./rudder-sources: ./rudder-sources.tar.bz2
	tar -xjf rudder-sources.tar.bz2
	mv rudder-sources-*/ rudder-sources/

./relay-api/virtualenv.tgz: /usr/bin/wget
	# Original URL: https://pypi.python.org/packages/source/v/virtualenv/virtualenv-12.0.7.tar.gz
	$(WGET) -O relay-api/virtualenv.tgz http://www.normation.com/tarball/virtualenv/virtualenv-$(VIRTUALENV_RELEASE).tar.gz

./relay-api/virtualenv/virtualenv.py: ./relay-api/virtualenv.tgz
	cd relay-api && tar -xzf ./virtualenv.tgz
	cd relay-api && mv ./virtualenv-$(VIRTUALENV_RELEASE)/ virtualenv/

./relay-api/virtualenv-1.10.1.tgz: /usr/bin/wget
	# Original URL: https://pypi.python.org/packages/source/v/virtualenv/virtualenv-1.10.1.tar.gz
	cd relay-api && $(WGET) -O virtualenv-1.10.1.tgz http://www.normation.com/tarball/virtualenv/virtualenv-1.10.1.tar.gz

# This is needed for SLES11
./relay-api/virtualenv-1.10.1/virtualenv.py: ./relay-api/virtualenv-1.10.1.tgz
	cd relay-api && tar -xzf ./virtualenv-1.10.1.tgz

localclean:
	rm -rf ./rudder-sources

veryclean:
	rm -f ./rudder-sources.tar.bz2

.PHONY: localdepends localclean veryclean
