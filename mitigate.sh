git checkout test-features
git checkout main -- mydb.sqlite    # put the full DB back on the branch
git commit -m "Restore full DB"
git checkout main
git merge test-features