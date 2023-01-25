#!/bin/bash
# unencrypt, and un(tar/compress) 
# you'll need the private key and passphrase

BACKUP="${BACKUP:-encryptedfile}"
TARARGS="${TARARGS:- }"  # -C destination/directory 
PRIVATE="${PRIVATE:-~/.ssh/private.key.pem}"
[[ ! -f $BACKUP ]] && echo "$BACKUP is not a file" && exit

IV=$(dd if=$BACKUP bs=33 count=1)
KEY=$(dd if=$BACKUP bs=384 count=1 iflag=skip_bytes skip=33 | openssl rsautl -decrypt -inkey $PRIVATE)

dd if=$BACKUP iflag=skip_bytes skip=417 | openssl enc -d -aes-256-cbc -K $KEY -iv $IV | tar -xzf - $TARARGS

