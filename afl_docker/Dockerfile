# Base off of AFL++
FROM aflplusplus/aflplusplus


# Move needed files
COPY ./afl_docker/env/* /home

# copy the config, logger, and examples
COPY ./config.cfg /env/
COPY ./lldb_docker/env/logger.sh /env/
COPY ./afl_docker/env/examples /env/examples

# chmod needed files
RUN chmod +x /home/init
RUN chmod +x /home/compile

# workdir
WORKDIR /home/
