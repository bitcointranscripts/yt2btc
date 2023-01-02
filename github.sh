# Make executable with chmod +x <<filename.sh>>
echo "What is your github username?"
read USERNAME

gh auth login

gh repo fork bitcointranscripts/bitcointranscripts --clone 

cd bitcointranscripts

git checkout -b ${2}

mv ${3} .

git add "$1" && git commit -m 'initial transcription using yt2btc script'

gh repo set-default ${USERNAME}/bitcointranscripts

gh pr create --base master --title "Autogenerated yt2btc" --body "youtube to bitcoin transcript" 

echo "Done"

