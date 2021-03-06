#!/usr/bin/python
'''
 (C) 2010-2013 ICM UW. All rights reserved.
'''
import os
import stat
import shutil
import string
import sys
import re
import wf_transformations
###############################################
######## DEFINITION BLOCK #####################
###############################################
def main(compilation_time, keywords, chrumprops, keys, combs, names, directory):
	plainName = ''
	idx = sys.argv[2].rfind('/')
	if idx == -1:
		plainName = sys.argv[2]
	else:
		plainName = sys.argv[2][idx+1:]
	
	full_exec = ['#!/usr/bin/python \n','import os\n']
	
	for idx,name in enumerate(names):
		calculateGivenCombination(compilation_time, keywords, chrumprops, keys, combs, names, directory, plainName, name, idx)
		full_exec.append('os.system(\'python '+directory+'/'+name+'/execute-in-oozie.py &'+'\')')
		
	f = open(directory+'/execute-all-in-oozie.py','w')
	f.write('\n'.join(full_exec)) 
	f.close()
	os.system('chmod +x '+directory+'/execute-all-in-oozie.py')

def rightSignOrZero(str):
	sto = str.rfind('/')
	if sto!=-1:
		return sto
	return 0
		
def rightSignOrMax(str):
	sto = str.rfind('/')
	if sto!=-1:
		return sto
	return len(str)

def leftSignOrZero(str):
	sto = str.find('/')
	if sto!=-1:
		return sto
	return 0

def substituteChrumWFProps(chrumProps,name,combs,keys,idx,compilation_time):
		f = open(chrumProps,'r')
		txt = 'COMPILATION_TIME='+compilation_time+'\nPARAMETER_COMBINATION='+name+'\n'+f.read()
		f.close()
		txt2 = []
		for li in txt.split('\n'): 
			for inner_idx, val in enumerate(combs[idx]):
				if re.search('^@'+keys[inner_idx]+'@',li):
					li = keys[inner_idx]+'='+combs[idx][inner_idx]
			txt2.append(li)
		f = open(chrumProps,'w')
		f.write('\n'.join(txt2))
		f.close()

def calculateGivenCombination(compilation_time, keywords, chrumprops, keys, combs, names, directory, plainName, name, idx):
		a = directory+'/default'
		b = directory+'/'+name
		shutil.copytree(a, b)
		
		substitutedWFPropertiesPath = directory+'/'+name+'/'+plainName 	
		substituteChrumWFProps(substitutedWFPropertiesPath,name,combs,keys,idx,compilation_time)
		
		execPath = sys.argv[0][:rightSignOrMax(sys.argv[0])]
#		sta = rightSignOrZero(sys.argv[3])
		wfname = 'workflow.xml'#sys.argv[3][sta:len(sys.argv[3])-len('.chrum')]
		sta = rightSignOrZero(sys.argv[2])
		finalWFPropertiesPath = directory+'/'+name+'/'+sys.argv[2][sta:len(sys.argv[2])-len('.chrum')]
#		finalWFPropertiesPath = directory+'/'+name+'/workflow.xml'

		wftxt = wf_transformations.main(execPath,substitutedWFPropertiesPath,sys.argv[3])
		substitutedWFXMLPath = directory+'/'+name+'/'+wfname
		f = open(substitutedWFXMLPath,'w')
		f.write(wftxt)
		f.close()
		
		hdfsProps = '/'.join([keywords['HDFS'],keywords['PROJECT'],compilation_time,name,plainName]) 
		hdfsPth = '/'.join([keywords['HDFS'],keywords['PROJECT'],compilation_time,name])
		hdfsSrc = '/'.join([keywords['HDFS'],keywords['PROJECT'],compilation_time,'default/*'])
		localWfSrc = directory+'/'+name+'/'+wfname
		subs = {'plain_name' : plainName, 
			'oozie_server' : keywords['OOZIE_SERVER'], 
			'oozie_port' : keywords['OOZIE_PORT'],
			'hdfs_wf_config' : hdfsProps,
			'hdfsPth' : hdfsPth,
			'hdfsSrc' : hdfsSrc,
			'localWfSrc' : localWfSrc,
			'substitutedWFPropertiesPath' : substitutedWFPropertiesPath,
			'finalWFPropertiesPath' : finalWFPropertiesPath,
			'substitutedWFXMLPath' : substitutedWFXMLPath
			}
  
		s = string.Template('\
#!/usr/bin/python \n\
import os	\n\
import stat	\n\
import time	\n\
import sys	\n\
\n\
#go to the executed script folder\n\
if sys.argv[0].rfind(\'/\') != -1:\n\
	path = sys.argv[0][:sys.argv[0].rfind(\'/\')]\n\
else:\n\
	path = os.getcwd()\n\
os.chdir(path)\n\
#perform cluster.properties substitution\n\
chrum_wf_props = \'/$substitutedWFPropertiesPath\'\n\
wf_props = \'/$substitutedWFXMLPath\'\n\
f = open(chrum_wf_props,\'r\')	\n\
txt = f.read()	\n\
f.close()	\n\
f = open(\'$finalWFPropertiesPath\',\'w\')	\n\
exec_time=str(time.time())	\n\
f.write(\'\
EXECUTION_TIME=\'+exec_time+\'\\n\
HDFS_EXEC_PATH=\\\n\
$hdfsPth/\'+exec_time+\'/\\n\'\
+txt)\n\
f.close()    \n\
#create folder on HDFS\n\
os.system(\'hadoop fs -mkdir $hdfsPth/\'+exec_time+\'/\')	\n\
#add all created files\n\
os.system(\'hadoop fs -put $localWfSrc  $hdfsPth/\'+exec_time+\'/\')	\n\
os.system(\'hadoop fs -cp $hdfsSrc $hdfsPth/\'+exec_time+\'/\')	\n\
#list all added files\n\
#os.system(\'hadoop fs -ls $hdfsPth/\'+exec_time+\'/\')	\n\
#run oozie workflow\n\
os.system(\'oozie job -oozie http://$oozie_server:$oozie_port/oozie -config $finalWFPropertiesPath -run\')	\n\
#os.system(\'oozie job -oozie http://$oozie_server:$oozie_port/oozie -config $hdfsPth/\'+exec_time+\'/cluster.properties -run\')	\n\
')
		f = open(directory+'/'+name+'/execute-in-oozie.py','w')
		tete = s.safe_substitute(subs);
		#print tete
		f.write(tete)
		f.close()
		os.system('chmod +x '+directory+'/'+name+'/execute-in-oozie.py')
