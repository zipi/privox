#!/bin/bash
# provide arguments in environment variables or accept default
NAME="${NAME:-targetfilename}"
MYPASS="${MYPASS:-mypasswordfile}"
MYUDI="${MYUID:-myusername}"
REMOTE_HOST="${REMOTE_HOST:-myserverfqdn}"
PUBLIC="${PUBLIC:-~/.ssh/myrsa.pub.pem}"
SOURCE="${SOURCE:-~/directory/where/the/files/are}"
TARGET="${TARGET:-$NAME.tgz.aes}"

echo $NAME $REMOTE_HOST $SOURCE

exit

SSH="sshpass -f $MYPASS ssh -o StrictHostKeyChecking=no $MYUID@$REMOTE_HOST"
AES_KEY=$(openssl rand -hex 32)
AES_IV=$(openssl rand -hex 16)

echo $AES_IV | $SSH "cat > $TARGET"
echo $AES_KEY | openssl rsautl -encrypt -pubin -inkey sno-backup.pub.pem | $SSH "cat >> $TARGET"
tar -cz -C $SOURCE  -f - * | openssl enc -aes-256-cbc -K $AES_KEY -iv $AES_IV  | $SSH "cat >> $TARGET"
