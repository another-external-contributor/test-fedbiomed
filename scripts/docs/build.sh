#!/bin/bash

########################################################
## Build Script for creating versioning for documentation
#########################################################

cleaning() {
    #
    # do all cleaning here (normal ending or trapped signal)
    #
    # IMPORTANT! remove templates if version below v3.4 is removed from doc
    rm -fr sitemap.xml sitemap_tmp.py templates templates-backup
    git checkout ${CURRENT_BRANCH_NAME}
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

# Declare version whose API docs are not allowed
API_DOC_NOT_ALLOWED=(v3.1 v3.2 v3.3 v3.4)

CURRENT_BRANCH_NAME=$(git branch --show-current)


# Cannot build if uncommited changes (prevents `git checkout`, build fails with unclear errors messages)
if [ -n "$(git status --porcelain -u no)" ]; then
  echo "ERROR: cannot build with uncommited changes. Please commit them or stash them."
  exit 1
fi

# Base build directory
if [ -n "$1" ]; then
  BUILD_DIR="$1";
else
  BUILD_DIR='./public';
fi

# API doc branch to build
if [ -n "$2" ]; then
  APIDOC_BRANCH_NAME=$2;
else
  APIDOC_BRANCH_NAME=develop;
fi

# Parse git tag output
IFS=$' \n' read -r -d '' -a VERSIONS <<< "$(git branch -a --no-color | grep origin/publish | awk -F/ '{print $NF}' | sort -r -n)"

echo "### All versions ${VERSIONS[*]} ----------------------------------"
echo "### Building main repository -------------------------------------"


RECENT_VERSION="${VERSIONS[0]}"

# Copy sitemap as tmp to use it after checking out to other tags
cp scripts/sitemap.py sitemap_tmp.py

cp -rf templates templates-backup

# Building current/last version/repo into main build dir
./scripts/fedbiomed_doc.sh --branch $APIDOC_BRANCH_NAME build --verbose -d "$BUILD_DIR"

echo "### Building menu -----------------------------------------------"
echo $(python scripts/menu.py) > menu.json
mv menu.json "$BUILD_DIR/menu.json"

echo "### Removing folders that belongs to versions -------------------"
rm -fr "$BUILD_DIR/tutorials" \
   "$BUILD_DIR/getting-started" \
   "$BUILD_DIR/user-guide" \
   "$BUILD_DIR/developer"




for version in ${VERSIONS[*]}
do
    # IMPORTANT: Latest tag already comes while building main repo
    # into build main directory. That's why tt shouldn't be built again
    # to avoid conflicts
    #if [ "${VERSIONS[index]}" != "$RECENT_VERSION" ]; then

    if [ "$version" = "$RECENT_VERSION" ]; then
      VERSION_FOLDER="latest"
    else
      VERSION_FOLDER="$version"
    fi



    echo "### Building version ${version} FOLDER: ${VERSION_FOLDER} ----------------------------------------------"
    if [ ! -d "$BUILD_DIR/${VERSION_FOLDER}" ]; then
      mkdir "$BUILD_DIR/${VERSION_FOLDER}"
    fi
    git checkout "publish/${version}"
    git pull

    cp -rf templates-backup/* templates

    # API Doc does not exist for the version
    if [ x$(echo "${API_DOC_NOT_ALLOWED[*]}" | grep -o "$version") != x ]; then
       mkdocs build --strict --verbose -d "$BUILD_DIR/${VERSION_FOLDER}"
    else
      ./scripts/fedbiomed_doc.sh --branch "${version}" build --verbose -d "$BUILD_DIR/${VERSION_FOLDER}"
    fi

    echo "### Updating sitemap.xml -------------------------------------------------------------------------------"
    python sitemap_tmp.py --version "${VERSION_FOLDER}"


    # Remove unnecessary folder and file from version build directory
    rm -rf "$BUILD_DIR/${VERSION_FOLDER}/assets/img" \
       "$BUILD_DIR/${VERSION_FOLDER}/assets/doc" \
       "$BUILD_DIR/${VERSION_FOLDER}/assets/resources" \
       "$BUILD_DIR/${VERSION_FOLDER}/pages" \
       "$BUILD_DIR/${VERSION_FOLDER}/news" \
       "$BUILD_DIR/${VERSION_FOLDER}/sitemap.xml" \
       "$BUILD_DIR/${VERSION_FOLDER}/index.html"

    # Files those have to be same in every version
    cp -r "$BUILD_DIR/assets/javascript/theme.js" "$BUILD_DIR/${VERSION_FOLDER}/assets/javascript/theme.js"
    cp -r "$BUILD_DIR/assets/css/style.css" "$BUILD_DIR/${VERSION_FOLDER}/assets/css/style.css"
    cp -r "$BUILD_DIR/index.html" "$BUILD_DIR/${VERSION_FOLDER}/index.html"

    git stash
done


# Copy final sitemap
echo "### Copying final sitemap into build directory --------------------------"
gzip -f -k sitemap.xml
cp -f sitemap.xml "$BUILD_DIR/" && cp -f sitemap.xml.gz "$BUILD_DIR/"

echo "### Building versions.json ----------------------------------------------"
VERSIONS_JSON='{"versions":{'
LAST="${VERSIONS[${#VERSIONS[@]} - 1]}"
for index in ${!VERSIONS[@]}
do
    if [ "$index" -eq "0" ]; then
        VERSIONS_JSON+='"latest":"'"${VERSIONS[index]}"'"'
    else
        VERSIONS_JSON+='"'"${VERSIONS[index]}"'":"'"${VERSIONS[index]}"'"'
    fi

    if [ "$LAST" != "${VERSIONS[index]}" ]; then
        VERSIONS_JSON+=','
    fi

done

# IMPORTANT: Please check DOC URL if it is changed
# Doc URL means: The URL at the top bar -> User Documentation
VERSIONS_JSON+='},"docurl":"getting-started/what-is-fedbiomed"}'
echo $VERSIONS_JSON > "$BUILD_DIR/versions.json"

cleaning
exit 0
