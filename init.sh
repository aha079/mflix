#! /bin/bash

source ./env.sh

mongorestore --drop --gzip --uri "$MFLIX_DB_URI" data/dump
