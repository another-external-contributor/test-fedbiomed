#!/bin/bash

########################################################
## Build Script for creating versioning for documentation
#########################################################


BASEDIR=$(cd $(dirname $0)/../.. || exit ; pwd)


cleaning() {
    if [ -d $BASEDIR/v$LATEST_TO_BUILD ]; then
        git worktree remove --force v$LATEST_TO_BUILD 
    fi

    if [ -d $BASEDIR/build-tmp ]; then
        rm -rf $BASEDIR/build-tmp
    fi
}

cleaning_trap() {
    #
    # script interruption
    #

    # avoid multiple CTLR-C from impatient users
    trap '' INT TERM
    cleaning
    exit 1
}

# do some cleaning then interrupted
trap cleaning_trap INT TERM

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
v_base=list(set([i[0:i.rindex('.')]  for i in y if y!= '']))
v_base=list(filter(lambda x: x != '', v_base))
v_base.sort(key=lambda s: [int(u) for u in s.split('.')])
print(' '.join(v_base) )

EOF
) || exit 1

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
    ) || exit 1

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
    ) || exit 1

    echo $T
}


redirect_to_latest () {

    # Redirect base URL to latest for documentation related URI path
  FILES_TO_REDIRECT='getting-started tutorials user-guide developer'
  for r in ${FILES_TO_REDIRECT}; do 
      echo "Creating redirection for $r"
      ./scripts/docs/redirect.py --source $BUILD_DIR_TMP/$r --base $BUILD_DIR_TMP -buri "/latest" || { cleaning; exit 1; }
  done

}

redirect_to_main () {

  if [ -z "$1" ]; then
    exit "No version is provided for function redirect to main"
  fi

  VERSION_FOR_REDIRECTION=$1

    # Redirect version base files
  FILES_TO_REDIRECT='index.html pages support news'
  for r in ${FILES_TO_REDIRECT}; do 
      echo "Creating redirection for $r"
      ./scripts/docs/redirect.py --source $BUILD_DIR_TMP/"$VERSION_FOR_REDIRECTION"/$r --base $BUILD_DIR_TMP -buri "../" || { cleaning; exit 1; }
  done

}

copy_to_build_dir () {


  VERSION_TO_LINK=$1
  rsync -q -av --checksum --progress $BUILD_DIR_TMP/. $BUILD_DIR --exclude CNAME --exclude .nojekyll --exclude .ssh --exclude .git --exclude .github || { cleaning; exit 1; }

  # Creat symbolik link
  if [ -n "$VERSION_TO_LINK" ]; then
    ln -r -sfn $BUILD_DIR/$VERSION_TO_LINK $BUILD_DIR/latest  || { cleaning; exit 1; }
  fi

  # Remove temprory files
  rm -rf $BUILD_DIR_TMP

}

set_build_environmnet () {

  if [ ! -d "$BUILD_DIR" ]; then 
    mkdir $BUILD_DIR
  fi 

}

create_version_json () {
    echo "Creating versions.json..........."
    ON_V=$(find "$BUILD_DIR" -maxdepth 1 -type d -name 'v[0-9].[0-9]*' -printf " %f" | sed -s 's/ //') || { cleaning; exit 1; }
    E_VERSIONS=($(sort_versions  "$ON_V")) || { cleaning; exit 1; }

    echo "Exsiting versions in documentation"
    echo ${E_VERSIONS[@]}

    LAST="${E_VERSIONS[${#E_VERSIONS[@]} - 1]}"
    VERSIONS_JSON='{"versions":{'
    for index in ${!E_VERSIONS[@]}
    do  
        if [ "${index}" -eq "0" ]; then
            VERSIONS_JSON+='"latest":"'"v${E_VERSIONS[index]}"'"'
        else
            VERSIONS_JSON+='"'"${E_VERSIONS[index]}"'":"'"v${E_VERSIONS[index]}"'"'
        fi

        if [ "$LAST" != "${E_VERSIONS[index]}" ]; then
            VERSIONS_JSON+=','
        fi

    done
    VERSIONS_JSON+='} }'
    echo $VERSIONS_JSON > "$BUILD_DIR/versions.json"


    echo "### Building menu -----------------------------------------------"
    echo $(python ./scripts/docs/menu.py) || exit 1 > $BUILD_DIR/menu.json 
}

build_current_as () {

  VERSION=$1
  if [ -z "$VERSION" ]; then 
    echo "Please give version name to build."
    exit 1
  fi

  BASE=$(echo "$VERSION" | sed 's/.[^.]*//3')
  ALREADY_CREATED=$(find $BUILD_DIR -maxdepth 1 -type d -name $BASE* -printf " %f") || exit 1

  mkdocs build -d "$BUILD_DIR_TMP"/"$VERSION" || { cleaning; exit 1; }


  # Redirect base URL to latest for documentation related URI path
  redirect_to_main 
  copy_to_build_dir "$VERSION"


  if [ -n "$ALREADY_CREATED" ]; then
    echo "Removing previous version: base of $BASE.x | except latest $VERSION" 
    for v in ${ALREADY_CREATED[@]}; do 
      if [ "$v" != "$VERSION" ]; then
          rm -rf $BUILD_DIR/$v
      fi
    done
  fi 

  create_version_json "$VERSION"
}


build_latest_version () {

  # Versions that does not have 'docs' directory
  VERISONS_NOT_ALLOWED_TO_BUILD="v3.0 v3.1 v3.2 v3.3 v3.4 v3.5 v4.0 v4.0.1 v4.1 v4.1.1 v4.1.2 v4.2 v4.2.1 v4.2.2"

  # All available versions
  VERSIONS=`git tag -l`

  VERSIONS_GIT=$(echo "$VERSIONS" | sed ':a;N;$!ba;s/\n/ /g' ) || exit 1
  echo "Versions in git: $VERSIONS_GIT"
  echo "$VERSIONS_GIT"
  BASES=( $(get_base_versions "$VERSIONS_GIT") ) || exit 1


  echo ${BASES[@]}
  LATEST_BASE="${BASES[-1]}"
  LATEST_TO_BUILD=$(get_latest_of_given_base "$VERSIONS_GIT" "$LATEST_BASE") || exit 1
  echo "Latest base:" $LATEST_BASE
  # This is to remove latest version that is already created before pushing vX.X.number

  ALREADY_CREATED=$(find $BUILD_DIR -maxdepth 1 -type d -name v$LATEST_BASE* -printf " %f") || exit 1


  echo "Available versions: "
  echo $VERSIONS

  set_build_environmnet
  
  if [ x$(echo "${VERISONS_NOT_ALLOWED_TO_BUILD[*]}" | grep -o "$LATEST_TO_BUILD") != x  ]; then 
    echo "$LATEST_TO_BUILD is not allowed to build"
    exit 1
  fi

  # Build latest version 
  # Create a new work tree to build latest version
  echo "Building version v$LATEST_TO_BUILD"
  git worktree add v"$LATEST_TO_BUILD"  v"$LATEST_TO_BUILD" || { cleaning; exit 1; }

  echo "Copying reference template"
  rsync -q -av --checksum --progress docs/.templates/. v"$LATEST_TO_BUILD"/docs/.templates/ --delete || { cleaning; exit 1; }

  # If docs is not existing build it from master
  
  if [ ! -d v"$LATEST_TO_BUILD"/docs ]; then
    mkdir "$BUILD_DIR_TMP"/v"$LATEST_TO_BUILD"/ || { cleaning; exit 1; }
    rsync -q -av --checksum --progress $BUILD_DIR_TMP/. $BUILD_DIR_TMP/v"$LATEST_TO_BUILD"/ --delete --exclude v"$LATEST_TO_BUILD" || { cleaning; exit 1; }
  else
    mkdocs build -d "$BUILD_DIR_TMP"/v"$LATEST_TO_BUILD" --config-file v"$LATEST_TO_BUILD"/mkdocs.yml || { cleaning; exit 1; }
  fi

  git worktree remove --force v"$LATEST_TO_BUILD" || { cleaning; exit 1; }


  # Redirect base URL to latest for documentation related URI path
  redirect_to_main "v$LATEST_TO_BUILD"
  copy_to_build_dir "v$LATEST_TO_BUILD"


  if [ -n "$ALREADY_CREATED" ]; then
    echo "Removing previous version: base of $v$LATEST_BASE.x | except latest v$LATEST_TO_BUILD" 
    echo $ALREADY_CREATED
    echo $LATEST_TO_BUILD
    for v in ${ALREADY_CREATED[@]}; do 
      if [ "$v" != "v$LATEST_TO_BUILD" ]; then
          rm -rf $BUILD_DIR/$v
      fi

    done
  fi 

  create_version_json

}


build_main () {

  set_build_environmnet

  # Build master documentation 
  # This is for main pages
  mkdocs build -d "$BUILD_DIR_TMP" || { cleaning; exit 1; }

  # Redirect base URL to latest for documentation related URI path
  redirect_to_latest 
  copy_to_build_dir 


}

BUILD_DIR="$BASEDIR"/build
BUILD_DIR_TMP="$BASEDIR"/build-tmp
BUILD_MAIN=
BUILD_LATEST_VERSION=
VERSION_TO_BUILD=
SERVE=
while :
  do
    case "$1" in
      --build-dir )

        BUILD_DIR=$(realpath $2) || exit 1
        shift 
        shift
        ;;
      --build-main )
        BUILD_MAIN=1
        shift 1
        ;;
      --build-latest-version )
        BUILD_LATEST_VERSION=1
        shift 1
        ;;

      --build-current-as ) 
        VERSION_TO_BUILD=$2
        shift
        shift

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

if [ -n "$SERVE" ]; then
  mkdocs serve
fi


if [ ! -d $BUILD_DIR ]; then
  echo "Error: $BUILD_DIR is not existing."
fi


if [ -n "$BUILD_MAIN" ]; then 
  echo "Building main"
  build_main
fi

if [ -n "$VERSION_TO_BUILD" ]; then 
  echo "Building version  $VERSION_TO_BUILD"
  build_current_as "$VERSION_TO_BUILD"
else 
  if [ -n "$BUILD_LATEST_VERSION" ]; then
    build_latest_version
  else
    echo "please specify --build-main, --build-current-as  or --build-latest-version "
    exit
  fi
fi








