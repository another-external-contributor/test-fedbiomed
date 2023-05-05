FROM python:3.8-alpine

RUN apk add --no-cache gcc g++ musl-dev linux-headers
RUN apk update && apk add bash && apk add git

COPY docs-requirements.txt docs-requirements.txt
RUN pip install -r docs-requirements.txt

