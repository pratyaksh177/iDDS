#!/bin/bash

instance=doma
if [ "$#" -eq 1 ]; then
  instance=$1
fi

export X509_USER_PROXY=/afs/cern.ch/user/w/wguan/workdisk/iDDS/test/x509up
export RUCIO_ACCOUNT=pilot

export PANDA_BEHIND_REAL_LB=true
#  export PANDA_SYS=/opt/idds/

if [ "$instance" == "k8s" ]; then
    export PANDA_AUTH=oidc
    export PANDA_URL_SSL=https://pandaserver-doma.cern.ch:25443/server/panda
    export PANDA_URL=http://pandaserver-doma.cern.ch:25080/server/panda
    export PANDAMON_URL=https://panda-doma.cern.ch
    export PANDA_AUTH_VO=panda_dev

    # export PANDA_CONFIG_ROOT=/afs/cern.ch/user/w/wguan/workdisk/iDDS/main/etc/panda/
    export PANDA_CONFIG_ROOT=~/.panda/
elif [ "$instance" == "slac" ]; then
    export PANDA_AUTH=oidc
    export PANDA_URL_SSL=https://rubin-panda-server-dev.slac.stanford.edu:443/server/panda
    export PANDA_URL=http://rubin-panda-server-dev.slac.stanford.edu:80/server/panda
    export PANDAMON_URL=https://rubin-panda-bigmon-dev.slac.stanford.edu
    export PANDA_AUTH_VO=Rubin

    # export PANDA_CONFIG_ROOT=/afs/cern.ch/user/w/wguan/workdisk/iDDS/main/etc/panda/
    export PANDA_CONFIG_ROOT=~/.panda/
else
    export PANDA_AUTH=oidc
    export PANDA_URL_SSL=https://pandaserver-doma.cern.ch:25443/server/panda
    export PANDA_URL=http://pandaserver-doma.cern.ch:25080/server/panda
    export PANDAMON_URL=https://panda-doma.cern.ch
    export PANDA_AUTH_VO=panda_dev
    
    export PANDACACHE_URL=$PANDA_URL_SSL

    export PANDA_SYS=/afs/cern.ch/user/w/wguan/workdisk/iDDS/.conda/iDDS/
    # export PANDA_CONFIG_ROOT=/afs/cern.ch/user/w/wguan/workdisk/iDDS/main/etc/panda/
    export PANDA_CONFIG_ROOT=~/.panda/
fi
