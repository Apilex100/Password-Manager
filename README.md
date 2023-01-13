
# Python Password Manager

A simple local password manager written in Python and MariaDB. Uses [pbkdf2](https://en.wikipedia.org/wiki/PBKDF2) to derive a 256 bit key from a MASTER PASSWORD and DEVICE SECRET to use with AES-256 for encrypting/decrypting.


# Installation
You need to have python3 to run this on Windows, Linux or MacOS
## Linux
### Install Python Requirements
```
sudo apt install python3-pip
pip install -r requirements.txt
```

### MariaDB
#### Install MariaDB on linux with apt
```
sudo apt update
sudo apt install mariadb-server mariadb-client -y
```

## Windows
### Install Python Requirements
```pip install -r requirements.txt```

### MariaDB
#### Install
Follow [these instructions](https://www.dataquest.io/blog/install-mysql-windows/) to install MariaDB on Windows

## Run
### Configure

You need to first configure the password manager by choosing a MASTER PASSWORD. This config step is only required to be executed once.
```
python config.py
```
The above command will make a new configuration by asking you to choose a MASTER PASSWORD.

### Usage
```
python pm.py -h
usage: pm.py [-h] [-s NAME] [-u URL] [-e EMAIL] [-l LOGIN] [--length LENGTH] [-c] option

Description

positional arguments:
  option                (a)dd / (e)xtract / (g)enerate

optional arguments:
  -h, --help            show this help message and exit
  -s NAME, --name NAME  Site name
  -u URL, --url URL     Site URL
  -e EMAIL, --email EMAIL
                        Email
  -l LOGIN, --login LOGIN
                        Username
  --length LENGTH       Length of the password to generate
  -c, --copy            Copy password to clipboard
```


### Add entry
```
python pm.py add -s mysite -u mysite.com -e hello@email.com -l myusername
```
### Retrieve entry
```
python pm.py extract
```
The above command retrieves all the entries
```
python pm.py e -s mysite
```
The above command retrieves all the entries whose site name is "mysite"
```
python pm.py e -s mysite -l myusername
```
The above command retrieves the entry whose site name is "mysite" and username is "myusername"
```
python pm.py e -s mysite -l myusername --copy
```
The above command copies the password of the site "mysite" and username "myusername" into the clipboard
### Generate Password
```
python pm.py g --length 15
```
The above command generates a password of length 15 and copies to clipboard
