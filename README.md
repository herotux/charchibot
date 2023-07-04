# charchibot

#install git

```
apt update
apt install git
```

#clone this repo

```
git clone https://github.com/herotux/charchibot.git
```

##first rename Sampleconfigfile.ini

```
cd charchibot

mv Sampleconfigfile.ini configfile.ini
```


##insert your parametrs in configfile to start bot normaly

```
nano configfile.ini
```

##install requirements and start bot

```
pip install pipenv
pipenv shell
cd carchibot
pipenv install -r requirement.txt
python xbot.py &
```
