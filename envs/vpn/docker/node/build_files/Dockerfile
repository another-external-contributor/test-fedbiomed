FROM fedbiomed/vpn-base

ARG CONTAINER_GID
ARG CONTAINER_UID
ARG CONTAINER_GROUP
ARG CONTAINER_USER
# assign default values even when variable exists and is empty
# (ARG default value only applies when variable is non existent)
# + make it persistent at runtime (pass this variable to container)
ENV CONTAINER_UID=${CONTAINER_UID:-root}
ENV CONTAINER_GID=${CONTAINER_GID:-root}
# alpine does not accept users/groups with numerical names
ENV CONTAINER_USER=${CONTAINER_USER:-root}
ENV CONTAINER_GROUP=${CONTAINER_GROUP:-root}

RUN apt-get update && apt-get install -y apt-utils wget

RUN [ "$CONTAINER_GROUP" != 'root' ] && groupadd -g $CONTAINER_GID $CONTAINER_GROUP || :
RUN [ "$CONTAINER_USER" != 'root' ] && useradd -m -d /home/$CONTAINER_USER \
        -u $CONTAINER_UID -g $CONTAINER_GID -s /bin/bash $CONTAINER_USER || :

# Install miniconda
RUN wget -q --directory-prefix=$HOME https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh && \
        bash $HOME/Miniconda3-latest-Linux-x86_64.sh -b -p /miniconda && \
        rm -f $HOME/Miniconda3-latest-Linux-x86_64.sh
# easier to install in a fixed path, not in alternate account home :
# cannot use "ENV PATH=${PATH}:${HOME}/miniconda/bin" : wont work because
# ${HOME} not defined in ENV command, only in RUN/etc. (executing in subshell)
ENV PATH=${PATH}:/miniconda/bin

COPY ./envs/vpn/docker/node/build_files/entrypoint.sh /
# Setup subset of fedbiomed code tree
RUN mkdir /fedbiomed
# Copy files from fedbiomed repo - in the context of fedbiomed top directory
COPY envs /fedbiomed/envs
COPY fedbiomed /fedbiomed/fedbiomed
COPY scripts /fedbiomed/scripts
# Alternative option : git clone & strip unused dirs
#  - ensures working with clean repo (docker build begins with a stat(), hangs for 
#    a long time if you have zillion files in notebooks/data)
#  - ensures using develop branch (good or bad)

# Prepare for work in context of alternate account
RUN chown -R $CONTAINER_USER:$CONTAINER_GROUP /fedbiomed
WORKDIR /fedbiomed
USER $CONTAINER_USER:$CONTAINER_GROUP

# Configure conda env in context of alternate account
RUN conda env update --file ./envs/vpn/conda/fedbiomed-node.yaml
# another option : add tag to configure script to call "./scripts/configure_conda fedbiomed-node"

# Launch as root to manage VPN
USER root:root
ENTRYPOINT ["/entrypoint.sh"]
