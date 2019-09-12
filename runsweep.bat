pushd D:\synced\Dropbox\simplenote
python L:\bin\sweeptext.py -refile '/^\[{tag}\] ' -clean -from "_inbox.txt" -to "{tag}.txt"
python L:\bin\sweeptext.py -collect '#todo' -link -headers -from "*" -exclude "/(collected).txt/" -to "#todo (collected).txt"
python L:\bin\sweeptext.py -collect '#errands' -link -headers -from "*" -exclude "/(collected).txt/" -to "#errands (collected).txt"
popd