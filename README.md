# charchibot


##first rename Sampleconfigfile.ini

```
mv Sampleconfigfile.ini configfile.ini
```


##insert your parametrs in configfile to start bot normaly

```
nano configfile.ini
```

##install requirements and start bot

```
apt update
pip install pipenv
pipenv shell
pipenv install -r requirement.txt
python xbot.py &
```