#!/usr/bin/env bash
pip3 install -r requirements.txt --user

if [ ! -f profile/nls/en_us.txt ]
then
	cp template/nsl/en_us.txt profile/nls/en_us.txt
fi
