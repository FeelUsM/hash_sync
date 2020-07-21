import winreg as reg
from tree_tools import *
#import json_diff as jd

import os
import os.path
home_dir = os.getcwd()
print(home_dir)
import datetime as dt
from datetime import *
curtz = datetime.now().astimezone().tzinfo
tform = '%Y-%m-%d %H-%M-%S%z'
from FileSystem import normalize_path, nested_join

#stat = {}
def scan_key(key,path=()):
    nkeys,nvals,chdate = reg.QueryInfoKey(key)
    #errors = {}
    root = {}
    for i in range(nkeys):
        try:
            name = reg.EnumKey(key,i)
        except WindowsError as e:
            print(path,i,nkeys)
            break
        err = False
        try:
            name_key = reg.OpenKey(key,name)
        except WindowsError as e:
            root['/'+name] = [-1,str(e)]
            err = True
            #print(path+(name,))
        if not err:
            root['/'+name] = scan_key(name_key,path+(name,))

    for i in range(nvals):
        name,val,typ = reg.EnumValue(key,i)
        #if typ==reg.REG_QWORD:
        #    val=str(val)
        if type(val)==bytes:
            val=repr(val)
        root['_'+name]=[typ,val]
        #stat[typ] = [path+(name,),val]
    return root

def scan_reg():
	return {
		'HKEY_CLASSES_ROOT'    :scan_key(reg.HKEY_CLASSES_ROOT    ,('HKEY_CLASSES_ROOT',)),
		'HKEY_CURRENT_USER'    :scan_key(reg.HKEY_CURRENT_USER    ,('HKEY_CURRENT_USER',)),
		'HKEY_LOCAL_MACHINE'   :scan_key(reg.HKEY_LOCAL_MACHINE   ,('HKEY_LOCAL_MACHINE',)),
		'HKEY_USERS'           :scan_key(reg.HKEY_USERS           ,('HKEY_USERS',)),
		'HKEY_PERFORMANCE_DATA':scan_key(reg.HKEY_PERFORMANCE_DATA,('HKEY_PERFORMANCE_DATA',)),
		'HKEY_CURRENT_CONFIG'  :scan_key(reg.HKEY_CURRENT_CONFIG  ,('HKEY_CURRENT_CONFIG',)),
	}
	
def reg_diff(old_root,root):
	""" Сравнивает 2 дерева, возвращает словари путь:файл/папка
		modified, - модифицированные файлы
		old, - файлы и папки, которые присутствуют только в старом дереве
		new, - файлы и папки, которые присутствуют только в новом дереве
		strict_old, 
		strict_new - файлы, которые превратились в папки, и папки, которые превратились в файлы,
			strict_old - из старого дерева (файл или папка)
			strict_new - из нового дерева (файл или папка)
		touched - файлы, у которых изменилось только время доступа
	"""
	old = {}
	new = {}
	modified_from = {}
	modified_to = {}
	def diff1(old_root,root,path):
		#nonlocal new
		#nonlocal old
		#nonlocal modified
		#nonlocal touched
		for name in root.keys():
			path_name = path+(name,)
			if type(root[name])==dict: # directory
				if name in old_root and type(old_root[name])==dict:
					# same dirs
					diff1(old_root[name],root[name],path_name)
				elif name in old_root:
					# file -> dir
					print('warning: file->dir :',my_path_join_a(*path_name))
					modified_from[path_name] = old_root[name]
					modified_to[path_name] =	 root[name]
				else:
					# new dir
					new[path_name] =	 root[name]
			else:# type(root[name])==list: # file
				if name in old_root and type(old_root[name])==dict:
					# dir -> file
					print('warning: dir->file :',my_path_join_a(*path_name))
					modified_from[path_name] = old_root[name]
					modified_to[path_name] =	 root[name]
				elif name in old_root:# and type(old_root[name])==list:
					# file -> file
					if old_root[name]!=root[name]:
						modified_from[path_name] = old_root[name]
						modified_to[path_name] =	 root[name]
				else:
					# new file
					new[path_name] =	 root[name]
		for name in old_root.keys():
			path_name = path+(name,)
			if name not in root:
				old[path_name] = old_root[name]
	diff1(old_root,root,())
	return {'old':old, 'new':new, 'modified_from':modified_from, 'modified_to':modified_to}

def action2tree(actions):
	tree = {}
	for action,pathlist in actions.items():
		for path,data in pathlist.items():
			path = tuple('/'+x for x in path)+(action,)
			set_subtree(tree,path,data)
	return tree
	
def reg_patch_compress(obj):
	obj = action2tree(obj)
	obj = nested_join(obj,'',lambda x: not x.startswith('/'),lambda x:x)
	return obj
	
def last_diff_reg(prefix,global_log=None):
	prefix_ = normalize_path(prefix+os.sep)
	emergency_dump = True
	newtime_s = None
	snapshot_json = None
	oldtime_s = None
	snapshot_bak = None
	root = None
	oldroot = None
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
	if '.reg' not in ld:
		# создаем папку
		newtime = datetime.now(curtz)
		newtime_s = newtime.strftime(tform)
		os.mkdir('.reg')
		print('create .reg/')
		with open('.reg/log.txt','a') as lf:
			lf.write(newtime_s+'\tcreate .reg\n')
		if global_log:
			with open(global_log,'a') as globlog:
				globlog.write(prefix+'\t'+newtime_s+'\tcreate ,reg\n')
		# записываем пустое дерево в .bak (дата на минуту раньше текущей)
		# сканируем-пересчитываем на основе .bak
		# затем сохраняем новый
		root = scan_reg()

		snapshot_json = '.reg/last_snapshot '+newtime_s+'.json'
		myjson_dump(root,snapshot_json)
		
		return
		
	elif not os.path.isdir('.reg'):
		raise Error(path+': .reg exist and is not dir')
	
	loclog = open('.reg/log.txt','a')
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
		snapshot_json = '.reg/last_snapshot '+newtime_s+'.json'
		def find_date_file(prefix,postfix,ls):
			return [s[len(prefix):-len(postfix)] for s in ls if  s.startswith(prefix) and s.endswith(postfix)]
		
		ls = os.listdir('.reg'+os.sep)
		bak_list = find_date_file('last_snapshot ','.bak',ls)
		last_list = find_date_file('last_snapshot ','.json',ls)
		assert len(bak_list)<=1, bak_list
		assert len(last_list)<=1, last_list
		
		if len(last_list) and len(bak_list): # есть last есть bak
			# загружаю bak->old 
			# загружаю last->new
			print('fast recovery')
			oldtime_s = bak_list[0]
			
			snapshot_bak = '.reg/last_snapshot '+oldtime_s+'.bak'
			oldroot = myjson_load(snapshot_bak) # <----
			
			snapshot_json = '.reg/last_snapshot '+last_list[0]+'.json'
			root = myjson_load(snapshot_json) # <----
			
		elif len(last_list) and len(bak_list)==0: # есть last нет bak
			# загружаю last->old
			# сканирую(old)->new
			# переименовываю last->bak
			# записываю new->last
			print('simple update')
			oldtime_s = last_list[0]
			
			snapshot_json = '.reg/last_snapshot '+oldtime_s+'.json'
			oldroot = myjson_load(snapshot_json) # <----

			root = scan_reg()
			
			snapshot_bak = '.reg/last_snapshot '+oldtime_s+'.bak'
			os.rename(snapshot_json,snapshot_bak)

			myjson_dump(root,'.reg/last_snapshot '+newtime_s+'.json') # ---->
			
		elif len(last_list)==0 and len(bak_list): # нет last есть bak
			# загружаю bak->old
			# сканирую(old)->new
			# записываю new->last
			print('recovery')
			oldtime_s = bak_list[0]
			
			snapshot_bak = '.reg/last_snapshot '+oldtime_s+'.bak'
			oldroot = myjson_load(snapshot_bak) # <----

			root = scan_reg()
			
			myjson_dump(root,'.reg/last_snapshot '+newtime_s+'.json') # ---->
			
		else:# len(last_list)==0 and len(bak_list)==0: # нет last нет bak
			# сканирую->new
			# записываю new->last
			# return
			print('create')
			
			root = scan_reg()

			snapshot_json = '.reg/last_snapshot '+newtime_s+'.json'
			myjson_dump(root,snapshot_json)
			
			return
			
	except BaseException as e:
		error(Exception('scan:',e));        return

	try:
		#print('old:',oldroot.keys())
		#print('new:',root.keys())
		#comp = jd.Comparator()
		
		#return oldroot,root,comp
		
		patch1 = reg_diff(oldroot,root)
		#return patch
		patch = reg_patch_compress(patch1)
		#print('patch:',patch.keys())
		
		#return oldroot,root,patch

		#newoldroot = hash_back_patch(root_d,*hash_patch_uncompress(patch['root']))
		#assert oldroot_d==newoldroot

		#newerrors = path_patch(olderrors,*path_patch_uncompress(patch['errors']))
		#assert errors==newerrors
	except BaseException as e:
		if emergency_dump:
			print('exception catched, writing "exception_dump.json"')
			with open('.reg/exception_dump.json','w') as file:
				json.dump({'oldroot':oldroot, 'root':root}, file)
		error(Exception('diff:',e));        return
		
	try:
		
		#print('patch:',patch.keys())
		myjson_dump(patch,'.reg/patch '+oldtime_s+' to '+newtime_s+'.json')
		if find_date_file('first_snapshot ','.json',ls):
			os.remove(snapshot_bak)
		else:
			os.rename(snapshot_bak,'.reg/first_snapshot '+oldtime_s+'.json',)
	except BaseException as e:
		error(Exception('scan:',e));        return
		
	loclog.close()
	if globlog: globlog.close()
	#return oldroot,root,patch,patch1

if __name__ == '__main__':
	import sys
	if len(sys.argv)<2:
		print('syntax: reg_diff prefix [global_log]')
		exit(1)
	prefix = sys.argv[1]
	global_log =  sys.argv[2] if len(sys.argv)>=3 else None
	print('prefix:',prefix)
	print('global_log:',global_log)
	last_diff_reg(prefix,global_log)
	
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
