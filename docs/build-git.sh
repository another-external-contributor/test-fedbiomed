#!/bin/bash

########################################################
## Build Script for creating versioning for documentation
#########################################################


BASEDIR=$(cd $(dirname $0)/.. || exit ; pwd)





# Converts string to an integer
int () { 
    printf '%d' ${1:-} 2> /dev/null || : 
}

# Gets base versions
get_base_versions () {
    
    T=$(python - << EOF
import re
y="$1".split(' ');
y=[i.replace('v', '') for i in y]
v_base=list(set([re.sub("^([^\.]+\.[^\.]+)\..*", "", i )  for i in y if y!= '']))
v_base=list(filter(lambda x: x != '', v_base))
v_base.sort(key=lambda s: [int(u) for u in s.split('.')])
print(' '.join(v_base) )

EOF
)

    echo $T
}

# Get latests version of given base version
get_latest_of_given_base () {


    T=$(
python - << EOF
import re
versions="$1".split(' ');
versions=[i.replace('v', '') for i in versions]


n=list(filter(lambda version: re.match(r'^$2', version), versions))
n.sort(key=lambda s: [int(u) for u in s.split('.')])
print(n[-1])
EOF
    )

    echo $T
}


# Verison to build
VERSION=$1

# All available versions
VERSIONS=`git tag -l`

# Declare version whose API docs are not allowed
VERSION_BULD_STARTS_FROM=$(int $(echo v4.2.1 | sed 's/v//;s/\.//g' | awk '{while(length<3) $0=$0 "0"}1'))

# Versions that does not have 'docs' directory
VERISONS_NOT_ALLOWED="v3.0 v3.1 v3.2 v3.3 v3.4 v3.5 v4.0 v4.0.1 v4.1 v4.1.1 v4.1.2 v4.2 v4.2.1 v4.2.2 v4.2.3 v4.2.4"


build_with_verison_tags () {
    
    # if [ x$(echo "${API_DOC_NOT_ALLOWED[*]}" | grep -o "$version") != x ]; then
    #    mkdocs build --strict --verbose -d "$BUILD_DIR/${VERSION_FOLDER}"
    # else
    #   ./scripts/fedbiomed_doc.sh --branch "${version}" build --verbose -d "$BUILD_DIR/${VERSION_FOLDER}"

    # fi
    VERSIONS=$(echo "$VERSIONS" | sed ':a;N;$!ba;s/\n/ /g' )
    
    BASES=$(get_base_versions "$VERSIONS")

    echo "$VERSIONS"
    for b in ${BASES}; do
        VERSION_FOLDER_NAME=$b
        VERSION_TO_BUILD=$(get_latest_of_given_base "$VERSIONS" "$b")
        echo "$VERSION_FOLDER_NAME $VERSION_TO_BUILD"
        echo "---------------------"
    done
}



build_with_verison_tags

BUILD_DIR=build

while :
  do
    case "$1" in
      --build-dir )
        BUILD_DIR=$2
        shift 
        shift
        ;;
      --buid-with-version-tags )
        BUILD_WITH_VERISON_TAGS=1
        shift 1
        ;;
      -s | --serve | serve )
        SERVE=1
        shift 1
        ;;
      -h | --help)
        exit 2
        ;;
      *)
        ARGS="$@"
        break
        ;;
    esac
  done




# Build documentation
$BASEDIR/docs/scripts/fedbiomed_doc.sh build --verbose -d "$BUILD_DIR"
