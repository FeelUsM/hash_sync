#!/usr/bin/env python
# coding: utf-8

# In[1]:


from FileSystem import *
from tree_tools import *
import os
import os.path
home_dir = os.getcwd()
print(home_dir)
import datetime as dt
from datetime import *
curtz = datetime.now().astimezone().tzinfo
tform = '%Y-%m-%d %H-%M-%S%z'
import re
import json


# In[2]:


from copy import *
def last_diff_dir(prefix,exclude_dirs=set(),global_log=None):
	prefix_ = normalize_path(prefix+os.sep)
	emergency_dump = True
	newtime_s = None
	snapshot_json = None
	oldtime_s = None
	snapshot_bak = None
	root = None
	oldroot = None
	errors = None
	olderrors = None
	patch = None
	try:
		os.chdir(prefix_)
		ld = os.listdir('.')
	except Exception as e:
		if global_log:
			with open(global_log,'a') as gl:
				gl.write(prefix+'\t'+'device unavailable\n')
			return
		else:
			raise e
	if '.files' not in ld:
		# создаем папку
		newtime = datetime.now(curtz)
		newtime_s = newtime.strftime(tform)
		os.mkdir('.files')
		print('create all')
		with open('.files/log.txt','a') as lf:
			lf.write(newtime_s+'\tcreate all\n')
		if global_log:
			with open(global_log,'a') as globlog:
				globlog.write(prefix+'\t'+newtime_s+'\tcreate all\n')
		# записываем пустое дерево в .bak (дата на минуту раньше текущей)
		# сканируем-пересчитываем на основе .bak
		# затем сохраняем новый
		errors,root = scan(prefix_,exclude_dirs)
		calc_hashes(errors,root,{},prefix)

		snapshot_json = '.files/last_snapshot '+newtime_s+'.json'
		dump_snapshot(errors,root,snapshot_json)
		
		return
		
	elif not os.path.isdir('.files'):
		raise Error(path+': .files exist and is not dir')
	
	loclog = open('.files/log.txt','a')
	globlog = open(global_log,'a') if global_log else None
	def log(s):
		s = str(s)[:200]
		print(s)
		loclog.write(s+'\n')
		loclog.flush()
		if globlog:
			globlog.write(prefix+'\t'+s+'\n')
			globlog.flush()
	def error(e):
		log(e)
		if not globlog:
			raise e
	
	try:
		newtime = datetime.now(curtz)
		newtime_s = newtime.strftime(tform)
		log(prefix_+'\t'+newtime_s)
		snapshot_json = '.files/last_snapshot '+newtime_s+'.json'
		def find_date_file(prefix,postfix,ls):
			return [s[len(prefix):-len(postfix)] for s in ls if  s.startswith(prefix) and s.endswith(postfix)]
		
		ls = os.listdir('.files'+os.sep)
		bak_list = find_date_file('last_snapshot ','.bak',ls)
		last_list = find_date_file('last_snapshot ','.json',ls)
		assert len(bak_list)<=1, bak_list
		assert len(last_list)<=1, last_list
		
		if len(last_list) and len(bak_list): # есть last есть bak
			# загружаю bak->old 
			# загружаю last->new
			print('fast recovery')
			oldtime_s = bak_list[0]
			
			snapshot_bak = '.files/last_snapshot '+oldtime_s+'.bak'
			olderrors,oldroot = load_snapshot(snapshot_bak) # <----
			
			snapshot_json = '.files/last_snapshot '+last_list[0]+'.json'
			errors,root = load_snapshot(snapshot_json) # <----
			
		elif len(last_list) and len(bak_list)==0: # есть last нет bak
			# загружаю last->old
			# сканирую(old)->new
			# переименовываю last->bak
			# записываю new->last
			print('simple update')
			oldtime_s = last_list[0]
			
			snapshot_json = '.files/last_snapshot '+oldtime_s+'.json'
			olderrors,oldroot = load_snapshot(snapshot_json) # <----

			errors,root = scan(prefix_,exclude_dirs)
			calc_hashes(errors,root,oldroot,prefix)
			
			snapshot_bak = '.files/last_snapshot '+oldtime_s+'.bak'
			os.rename(snapshot_json,snapshot_bak)

			dump_snapshot(errors,root,'.files/last_snapshot '+newtime_s+'.json') # ---->
			
		elif len(last_list)==0 and len(bak_list): # нет last есть bak
			# загружаю bak->old
			# сканирую(old)->new
			# записываю new->last
			print('recovery')
			oldtime_s = bak_list[0]
			
			snapshot_bak = '.files/last_snapshot '+oldtime_s+'.bak'
			olderrors,oldroot = load_snapshot(snapshot_bak) # <----

			errors,root = scan(prefix_,exclude_dirs)
			calc_hashes(errors,root,oldroot,prefix)
			
			dump_snapshot(errors,root,'.files/last_snapshot '+newtime_s+'.json') # ---->
			
		else:# len(last_list)==0 and len(bak_list)==0: # нет last нет bak
			# сканирую->new
			# записываю new->last
			# return
			print('create')
			
			errors,root = scan(prefix_,exclude_dirs)
			calc_hashes(errors,root,{},prefix)

			snapshot_json = '.files/last_snapshot '+newtime_s+'.json'
			dump_snapshot(errors,root,snapshot_json)
			
			return
			
	except BaseException as e:
		error(Exception('scan:',e));        return

	try:
		oldroot_d = oldroot#{k:v for k,v in oldroot.items() if k!='__scan_errors__'}
		root_d = root#{k:v for k,v in root.items() if k!='__scan_errors__'}

		patch = {
			'errors':path_patch_compress(*path_diff(olderrors,errors)),
			'root':hash_patch_compress(*hash_diff(oldroot_d,root_d))
		}

		newoldroot = hash_back_patch(root_d,*hash_patch_uncompress(patch['root']))
		assert oldroot_d==newoldroot

		newerrors = path_patch(olderrors,*path_patch_uncompress(patch['errors']))
		assert errors==newerrors
	except BaseException as e:
		if emergency_dump:
			print('exception catched, writing "exception_dump.json"')
			with open('.files/exception_dump.json','w') as file:
				json.dump({'olderrors':olderrors,'errors':errors,'oldroot':oldroot,
						   'root':root},      file)
		error(Exception('diff:',e));        return
		
	try:
		myjson_dump(patch,'.files/patch '+oldtime_s+' to '+newtime_s+'.json')
		if find_date_file('first_snapshot ','.json',ls):
			os.remove(snapshot_bak)
		else:
			os.rename(snapshot_bak,'.files/first_snapshot '+oldtime_s+'.json',)
	except BaseException as e:
		error(Exception('scan:',e));        return
		
	loclog.close()
	if globlog: globlog.close()

if __name__ == '__main__':
	import sys
	if len(sys.argv)<2:
		print('syntax: scan_diff prefix [global_log [exclude_dirs...]]')
		exit(1)
	prefix = sys.argv[1]
	global_log =  sys.argv[2] if len(sys.argv)>=3 else None
	exclude_dirs = set()
	for i in range(3,len(sys.argv)):
		exclude_dirs.add(sys.argv[i])
	print('prefix:',prefix)
	print('global_log:',global_log)
	print('exclude_dirs:',exclude_dirs)
	last_diff_dir(prefix,exclude_dirs,global_log)
	
if False:
	# # ---- DISKS  -----

	global_log = r'D:\Users\feelus\Desktop\scan-diff.log'

	last_diff_dir('D:',{r'D:\Users\feelus\YandexDisk',r'D:\$RECYCLE.BIN'},global_log)
	# executed in 8m 51s, finished 22:38:19 2020-07-13
	# executed in 7m 58s, finished 14:15:46 2020-07-14 149 GB


	last_diff_dir('C:',{r'C:\$RECYCLE.BIN'},global_log)
	# executed in 11m 20s, finished 11:55:56 2020-07-14 
	# executed in 10m 5s, finished 14:25:51 2020-07-14 142 GB

	#patch 2020-05-31 11-40-04+0300 to 2020-07-02 23-29-48+0300.json
	# Program Files/Mozilla Firefox/chrome.manifest
	#  файлы размера 0 содержится и в moved и в new/old

	last_diff_dir(r'D:\Users\feelus\YandexDisk',{},global_log)
	# executed in 1m 4.46s, finished 14:26:56 2020-07-14 207 GB


	last_diff_dir('H:',{r'H:\$RECYCLE.BIN'},global_log)
	# executed in 1.56s, finished 14:26:57 2020-07-14 343 GB

	last_diff_dir('I:',{r'I:\$RECYCLE.BIN'},global_log)
	# executed in 12m 44s, finished 14:39:42 2020-07-14 330 GB

	#os.system("shutdown /s /t 1");
