#!/bin/bash

########################################################
## Build Script for creating versioning for documentation
#########################################################


BASEDIR=$(cd $(dirname $0)/../.. || exit ; pwd)




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


sort_versions () {
      T=$(
python - << EOF
import re
versions="$1".split(' ');
versions=[i.replace('v', '') for i in versions]

versions.sort(key=lambda s: [int(u) for u in s.split('.')], reverse=True)
print(' '.join(versions))
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


build_single_version () {

  if [ ! -d "$BUILD_DIR" ]; then 
    mkdir $BUILD_DIR
  fi 

  VERSIONS_GIT=$(echo "$VERSIONS" | sed ':a;N;$!ba;s/\n/ /g' )
  BASES=( $(get_base_versions "$VERSIONS_GIT") )
  LATEST_BASE="${BASES[-1]}"
  LATEST_TO_BUILD=$(get_latest_of_given_base "$VERSIONS_GIT" "$LATEST_BASE")
  echo $LATEST_BASE
  # This is to remove latest version that is already created before pushing vX.X.number
  ALREADY_CREATED=$(find $BUILD_DIR -maxdepth 1 -type d -name v$LATEST_BASE* -printf "%f")
  echo "Removing previous version: base of $v$LATESTS_BASE.x" 
  rm -rf ALREADY_CREATED


  echo "### Building menu -----------------------------------------------"
  echo $(python ./scripts/docs/menu.py) > $BUILD_DIR/menu.json


  # Build master documentation 
  # This is for main pages
  $BASEDIR/scripts/docs/fedbiomed_doc.sh build -d "$BUILD_DIR_TMP"

  # Build latest version 
  # Create a new work tree to build latest version
  echo "Building version v$LATEST_TO_BUILD"
  git worktree add v"$LATEST_TO_BUILD"  v"$LATEST_TO_BUILD"

  # If docs is not existing build it from master
  if [ ! -d v"$LATEST_TO_BUILD"/docs ]; then
    mkdir "$BUILD_DIR_TMP"/v"$LATEST_TO_BUILD"/
    rsync -q -av --checksum --progress $BUILD_DIR_TMP/. $BUILD_DIR_TMP/v"$LATEST_TO_BUILD"/ --delete --exclude v"$LATEST_TO_BUILD"
  else
    FED_DOC_VERSION=v"$LATEST_TO_BUILD" $BASEDIR/scripts/docs/fedbiomed_doc.sh build --verbose -d "$BUILD_DIR_TMP"/v"$LATEST_TO_BUILD" --config-file v"$LATEST_TO_BUILD"/mkdocs.yml
  fi

  git worktree remove v"$LATEST_TO_BUILD"


  # Redirect base URL to latest for documentation related URI path
  FILES_TO_REDIRECT='getting-started tutorials user-guide developer'
  for r in ${FILES_TO_REDIRECT}; do 
      echo "Creating redirection for $r"
      ./scripts/docs/redirect.py --source $BUILD_DIR_TMP/$r --base $BUILD_DIR_TMP -buri "/latest"
  done

  # Redirect version base files
    FILES_TO_REDIRECT='index.html pages support news'
  for r in ${FILES_TO_REDIRECT}; do 
      echo "Creating redirection for $r"
      ./scripts/docs/redirect.py --source $BUILD_DIR_TMP/v"$LATEST_TO_BUILD"/$r --base $BUILD_DIR_TMP -buri "../"
  done

  rsync -q -av --checksum --progress $BUILD_DIR_TMP/. $BUILD_DIR --delete --exclude CNAME --exclude .nojekyll --exclude .ssh --exclude .git --exclude .github

  # Creat symbolik link
  ln -sf $BUILD_DIR/v$LATEST_TO_BUILD $BUILD_DIR/latest 

  # Remove temprory files
  rm -rf $BUILD_DIR_TMP

  echo "Creating versions.json..........."
  ON_V=$(find "$BUILD_DIR" -maxdepth 1 -type d -name 'v[0-9].[0-9]*' -printf " %f" | sed -s 's/ //')
  echo $ON_V
  E_VERSIONS=($(sort_versions  "$ON_V"))

  echo "Exsiting versions in documentation"
  echo $E_VERSIONS
  LAST="${E_VERSIONS[${#E_VERSIONS[@]} - 1]}"
  VERSIONS_JSON='{"versions":{'
  for index in ${!E_VERSIONS[@]}
  do  
      echo $index
      if [ "${index}" -eq "0" ]; then
          VERSIONS_JSON+='"latest":"'"${E_VERSIONS[index]}"'"'
      else
          VERSIONS_JSON+='"'"${E_VERSIONS[index]}"'":"'"${E_VERSIONS[index]}"'"'
      fi

      if [ "$LAST" != "${E_VERSIONS[index]}" ]; then
          VERSIONS_JSON+=','
      fi

  done
  VERSIONS_JSON+='} }'
  echo $VERSIONS_JSON > "$BUILD_DIR/versions.json"

}


#build_with_verison_tags

BUILD_DIR="$BASEDIR"/build
BUILD_DIR_TMP="$BASEDIR"/build-tmp

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



# Build docs
build_single_version

# Build documentation
# $BASEDIR/docs/scripts/fedbiomed_doc.sh build --verbose -d "$BUILD_DIR"
