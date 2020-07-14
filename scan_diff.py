from FileSystem import *
import os
home_dir = os.getcwd()
print(home_dir)
import datetime as dt
from datetime import *
curtz = datetime.now().astimezone().tzinfo
tform = '%Y-%m-%d %H-%M-%S%z'
import re
import json

def print_tree(obj):
	s = myjson_dumps(tree_dump(obj))
	# проверка на кол-во строк ...
	print(s)
def load_snapshot(path):
	tmp = clear_json_comment(myjson_load(path))
	return tree_load(tmp['root']),tree_load(tmp['errors'])
def dump_snapshot(root,errors,path):
	myjson_dump({
		'errors':tree_dump(errors),
		'root':tree_dump(root)
	},path)

	
newtime_s = None
snapshot_json = None
oldtime_s = None
snapshot_bak = None
root = None
oldroot = None
errors = None
olderrors = None
def last_diff_dir(prefix,prefix_,exclude_dirs,load_snapshot,dump_snapshot,emergency_dump=True):
	global newtime_s
	global oldtime_s
	global root
	global oldroot
	global errors
	global olderrors
	os.chdir(prefix_)
	newtime = datetime.now(curtz)
	newtime_s = newtime.strftime(tform)
	snapshot_json = '.files/last_snapshot '+newtime_s+'.json'
	def find_date_file(prefix,postfix,ls):
		return [s[len(prefix):-len(postfix)] for s in ls if \
				  s.startswith(prefix) and s.endswith(postfix)]
	if '.files' in os.listdir('.'):
		ls = os.listdir('.files\\')
		print('simple update')
		# сканируем-пересчитываем на основе json
		# затем переименовываем его в .bak и сохраняем новый
		oldtime_list = find_date_file('last_snapshot ','.json',ls)
		assert len(oldtime_list)==1
		oldtime_s = oldtime_list[0]
		snapshot_bak = '.files/snapshot '+oldtime_s+'.json'

		oldroot,olderrors = load_snapshot('.files/last_snapshot '+oldtime_s+'.json') # <----
		root,errors = scan(prefix_,exclude_dirs)
		calc_hashes(root,errors,oldroot,prefix)

		os.rename('.files/last_snapshot '+oldtime_s+'.json',snapshot_bak)
		dump_snapshot(root,errors,snapshot_json) # ---->

		try:
			oldroot_d = oldroot#{k:v for k,v in oldroot.items() if k!='__scan_errors__'}
			root_d = root#{k:v for k,v in root.items() if k!='__scan_errors__'}
			modified,old,new,strict_old,strict_new,touched = path_diff(oldroot_d,root_d)
			assert set(old)&set(strict_old) == set()
			assert set(new)&set(strict_new) == set()
			moved,old_dirs,new_dirs,old,new = hash_diff(old,new)
			assert set(old)&set(strict_old) == set()
			assert set(new)&set(strict_new) == set()

			newoldroot = hash_back_patch(root_d,modified,moved,old_dirs,new_dirs,
								  {**old,**strict_old},{**new,**strict_new},touched)
			#first_diff(root_d,new_root_d)
			assert oldroot_d==newoldroot

			e_modified,e_old,e_new,e_strict_old,e_strict_new,e_touched = path_diff(olderrors,errors)
			newerrors = path_patch(olderrors,e_modified,
								   {**e_old,**e_strict_old},{**e_new,**e_strict_new}, e_touched)
			assert errors==newerrors
			
			compressed_patch = {
				'errors':path_patch_dump(e_modified,e_old,e_new,e_strict_old,e_strict_new,e_touched),
				'root':hash_patch_dump(modified,moved,old_dirs,new_dirs,
									  {**old,**strict_old},{**new,**strict_new},touched)
			}
			
			patch_name = '.files/patch '+oldtime_s+' to '+newtime_s+'.json'
			myjson_dump(compressed_patch,patch_name)
			os.remove(snapshot_bak)
			with open('log.log','a+') as fl:
				print(patch_name,'created',file = fl)
		except BaseException as e:
			with open(home_dir+'/diff.log','a+') as fl:
				print(prefix,oldtime_s,newtime_s,'unable calc diff',file = fl)
				print(e,file = fl)
			with open('log.log','a+') as fl:
				print(oldtime_s,newtime_s,'unable calc diff',file = fl)
			
	else:
		print('create all')
		# записываем пустое дерево в .bak (дата на минуту раньше текущей)
		# сканируем-пересчитываем на основе .bak
		# затем сохраняем новый
		os.mkdir('.files')
		snapshot_bak = '.files/init_snapshot '+newtime_s+'.json'
		oldroot = {}
		root,errors = scan(prefix_,exclude_dirs)
		calc_hashes(root,errors,oldroot,prefix)

		dump_snapshot(root,errors,snapshot_bak) # ---->
		dump_snapshot(root,errors,snapshot_json)

#==============================================================================
# --- D ---

exclude_dirs = {r'D:\Users\feelus\YandexDisk',r'D:\$RECYCLE.BIN'}
prefix = 'D:'
prefix_ = prefix+'\\'
last_diff_dir(prefix,prefix_,exclude_dirs,load_snapshot,dump_snapshot)

# --- C ---

exclude_dirs = {r'C:\$RECYCLE.BIN'}
prefix = 'C:'
prefix_ = prefix+'\\'
def en_load_snapshot(path):
    with open(path,'r') as file:
        tmp = clear_json_comment(json.load(file))
    return tree_load(tmp['root']),tree_load(tmp['errors'])
def en_dump_snapshot(root,errors,path):
    with open(path,'w') as file:
        json.dump({
            'errors':tree_dump(errors),
            'root':tree_dump(root)
        },file,indent='\t')

last_diff_dir(prefix,prefix_,exclude_dirs,en_load_snapshot,en_dump_snapshot)

#--- YD ---

exclude_dirs = {}
prefix = r'D:\Users\feelus\YandexDisk'
prefix_ = prefix+'\\'
try:
	os.chdir(prefix_)
	canCD = True
except BaseException:
	canCD = False
if canCD:
	last_diff_dir(prefix,prefix_,exclude_dirs,load_snapshot,dump_snapshot)


#--- H ---

exclude_dirs = {r'H:\$RECYCLE.BIN'}
prefix = 'H:'
prefix_ = prefix+'\\'
try:
	os.chdir(prefix_)
	canCD = True
except BaseException:
	canCD = False
	with open(home_dir+'/diff.log','a+') as fl:
		print(datetime.now(curtz).strftime(tform),'device not available',file = fl)
if canCD:
	last_diff_dir(prefix,prefix_,exclude_dirs,load_snapshot,dump_snapshot)

#--- I ---

exclude_dirs = {r'I:\$RECYCLE.BIN'}
prefix = 'I:'
prefix_ = prefix+'\\'
try:
	os.chdir(prefix_)
	canCD = True
except BaseException:
	canCD = False
	with open(home_dir+'/diff.log','a+') as fl:
		print(datetime.now(curtz).strftime(tform),'device not available',file = fl)
if canCD:
	last_diff_dir(prefix,prefix_,exclude_dirs,load_snapshot,dump_snapshot)

#--- shutdown ---
import os
os.system("shutdown /s /t 1");
